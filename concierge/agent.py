import json
import threading

import anthropic
from django.conf import settings

from .models import NegotiationSession, Message
from .whatsapp import send_message

_client = anthropic.Anthropic()

_lock = threading.Lock()
_running = set()


def _build_system_prompt(session):
    p = session.prefs
    lines = [
        "You are the world66 Concierge. You contact travel providers on WhatsApp on behalf of travellers.",
        f"You are arranging a booking with {session.provider_name} for {session.user_name}.",
        "",
        "Traveller preferences:",
        f"  Dates: {p.get('dates', 'flexible')}",
        f"  Group size: {p.get('group_size', 'unspecified')}",
        f"  Notes: {p.get('notes', 'none')}",
    ]
    listed = p.get("listed_price")
    target = p.get("target_price")
    maximum = p.get("max_price")
    if listed or target or maximum:
        lines += [
            "",
            "Pricing mandate:",
            f"  Listed price: {listed or 'unknown'} per person",
            f"  Target price (aim for this): {target or 'listed price'}",
            f"  Maximum price (never exceed): {maximum or 'listed price'}",
            "",
            "Negotiate politely but assertively. Open by asking if they can accommodate the group "
            "and whether there is any flexibility on price. Do not reveal the maximum. "
            "If they won't come down to the target, try to split the difference. "
            "Never accept above the maximum.",
        ]
    lines += [
        "",
        "Rules:",
        "- Always present yourself as 'world66 Concierge', not as the traveller.",
        "- Be friendly, concise, and professional.",
        "- Confirm date/time, group size, programme, and final price before closing.",
        "- After at most 5 exchange rounds, call close_session.",
        "- If the provider is unresponsive or cannot meet requirements, close as failed.",
    ]
    return "\n".join(lines)


_TOOLS = [
    {
        "name": "send_whatsapp",
        "description": "Send a WhatsApp message to the provider.",
        "input_schema": {
            "type": "object",
            "properties": {
                "body": {"type": "string", "description": "Message text to send."}
            },
            "required": ["body"],
        },
    },
    {
        "name": "get_messages",
        "description": "Return the full message thread so far as a JSON array.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "close_session",
        "description": "Mark the session as agreed or failed and write a summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["agreed", "failed"],
                    "description": "Outcome of the negotiation.",
                },
                "summary": {
                    "type": "string",
                    "description": "Plain-English summary for the traveller.",
                },
            },
            "required": ["status", "summary"],
        },
    },
]


def _execute_tool(session, tool_name, tool_input):
    if tool_name == "send_whatsapp":
        body = tool_input["body"]
        sid = send_message(session.provider_whatsapp, body)
        Message.objects.create(session=session, direction="outbound", body=body, twilio_sid=sid)
        return "Message sent."

    if tool_name == "get_messages":
        msgs = list(
            session.messages.values("direction", "body", "timestamp")
        )
        for m in msgs:
            m["timestamp"] = m["timestamp"].isoformat()
        return json.dumps(msgs)

    if tool_name == "close_session":
        session.status = tool_input["status"]
        session.summary = tool_input["summary"]
        session.save(update_fields=["status", "summary", "updated_at"])
        return "Session closed."

    return f"Unknown tool: {tool_name}"


def run_agent(session_id):
    """Run (or resume) the agent for a session. Thread-safe: only one run per session at a time."""
    with _lock:
        if session_id in _running:
            return
        _running.add(session_id)
    try:
        _do_run(session_id)
    finally:
        with _lock:
            _running.discard(session_id)


def _do_run(session_id):
    session = NegotiationSession.objects.get(id=session_id)
    if session.status in ("agreed", "failed"):
        return

    session.status = "contacting" if not session.messages.exists() else "negotiating"
    session.save(update_fields=["status", "updated_at"])

    system = _build_system_prompt(session)

    msgs = list(session.messages.order_by("timestamp").values("direction", "body"))
    history = []
    for m in msgs:
        role = "assistant" if m["direction"] == "outbound" else "user"
        history.append({"role": role, "content": m["body"]})

    if not history:
        history.append({
            "role": "user",
            "content": (
                "Please introduce yourself to the provider and start arranging the booking "
                "according to the traveller's preferences."
            ),
        })

    while True:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=_TOOLS,
            messages=history,
        )

        # Append assistant turn to history
        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        closed = False
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = _execute_tool(session, block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })
            if block.name == "close_session":
                closed = True

        history.append({"role": "user", "content": tool_results})

        if closed:
            break
