import json
import threading

import anthropic
from django.conf import settings
from django.core.mail import send_mail

from .models import NegotiationSession, Message
from .whatsapp import send_message

_client = anthropic.Anthropic()

_lock = threading.Lock()
_running = set()


def _notify_user(session):
    if not session.user_email:
        return
    if session.status == "confirmed":
        subject = f"Booking confirmed — {session.provider_name}"
        outcome = "Great news — your booking is confirmed!"
    elif session.status == "cancelled":
        subject = f"No longer needed — {session.provider_name}"
        outcome = "We've cancelled this negotiation because a deal was reached with another provider."
    else:
        subject = f"Update from your world66 Concierge — {session.provider_name}"
        outcome = "The negotiation has ended."
    body = (
        f"Hi {session.user_name},\n\n"
        f"{outcome}\n\n"
        f"{session.summary}\n\n"
        f"— world66 Concierge\n"
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [session.user_email], fail_silently=True)


def _notify_user_offer(session):
    if not session.user_email:
        return
    offer = session.proposed_offer
    site_url = getattr(settings, "SITE_URL", "http://localhost:8066")
    session_url = f"{site_url}/concierge/session/{session.id}"
    subject = f"Offer received from {session.provider_name} — confirm?"
    body = (
        f"Hi {session.user_name},\n\n"
        f"Your world66 Concierge has received an offer from {session.provider_name}:\n\n"
        f"{offer.get('summary', '')}\n"
    )
    if offer.get("price"):
        body += f"\nPrice: {offer['price']} per person"
    if offer.get("date"):
        body += f"\nDate: {offer['date']}"
    body += (
        f"\n\nTo confirm this booking, visit:\n{session_url}\n\n"
        f"— world66 Concierge\n"
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [session.user_email], fail_silently=True)


def _cancel_siblings(confirmed_session):
    """Cancel all other sessions in the same group and notify their providers."""
    if not confirmed_session.group_id:
        return
    siblings = NegotiationSession.objects.filter(
        group_id=confirmed_session.group_id,
    ).exclude(id=confirmed_session.id).exclude(
        status__in=NegotiationSession.TERMINAL_STATUSES
    )
    for sibling in siblings:
        if sibling.provider_whatsapp:
            body = (
                "Hi, thank you very much for your time! We've managed to arrange something "
                "with another provider for this occasion. We hope to be in touch another time. "
                "Best regards, world66 Concierge."
            )
            try:
                sid = send_message(sibling.provider_whatsapp, body)
                Message.objects.create(
                    session=sibling, direction="outbound", body=body, twilio_sid=sid
                )
            except Exception:
                pass
        sibling.status = "cancelled"
        sibling.summary = f"Booking arranged with {confirmed_session.provider_name} instead."
        sibling.save(update_fields=["status", "summary", "updated_at"])
        _notify_user(sibling)


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
        "- NEVER accept an offer from the provider yourself. When they make a concrete offer "
        "  (date, price, programme), always call propose_to_user so the traveller can confirm.",
        "- Only call close_session if the provider is unresponsive or cannot meet requirements at all.",
        "- After at most 5 exchange rounds, either propose_to_user or close_session.",
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
        "name": "propose_to_user",
        "description": (
            "Forward a concrete offer from the provider to the traveller for confirmation. "
            "Call this whenever the provider quotes a price, date, or programme. "
            "Never accept an offer yourself — always forward it to the traveller via this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Plain-English summary of the offer for the traveller.",
                },
                "price": {"type": "string", "description": "Offered price per person."},
                "date": {"type": "string", "description": "Offered date and time."},
                "details": {
                    "type": "string",
                    "description": "Any other relevant details (programme, inclusions, etc).",
                },
            },
            "required": ["summary"],
        },
    },
    {
        "name": "close_session",
        "description": (
            "Mark the session as failed. Only use this if the provider is unresponsive "
            "or fundamentally cannot meet the traveller's requirements."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Plain-English explanation for the traveller.",
                },
            },
            "required": ["summary"],
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
        msgs = list(session.messages.values("direction", "body", "timestamp"))
        for m in msgs:
            m["timestamp"] = m["timestamp"].isoformat()
        return json.dumps(msgs)

    if tool_name == "propose_to_user":
        session.proposed_offer = tool_input
        session.status = "pending_confirmation"
        session.save(update_fields=["proposed_offer", "status", "updated_at"])
        _notify_user_offer(session)
        return "Offer forwarded to traveller. Waiting for their confirmation."

    if tool_name == "close_session":
        session.status = "failed"
        session.summary = tool_input["summary"]
        session.save(update_fields=["status", "summary", "updated_at"])
        _notify_user(session)
        return "Session closed as failed."

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


def confirm_booking(session_id):
    """Called when the user confirms an offer. Sends confirmation to provider and cancels siblings."""
    session = NegotiationSession.objects.get(id=session_id)
    if session.status != "pending_confirmation":
        return

    offer = session.proposed_offer
    confirmation = (
        f"Great news — the traveller has confirmed! "
        f"{offer.get('summary', 'We confirm the booking as discussed.')} "
        f"Please let us know if you need any further details. Thank you!"
    )
    msg = Message.objects.create(
        session=session, direction="outbound", body=confirmation
    )
    try:
        sid = send_message(session.provider_whatsapp, confirmation)
        msg.twilio_sid = sid
        msg.save(update_fields=["twilio_sid"])
    except Exception:
        pass

    session.status = "confirmed"
    session.summary = offer.get("summary", "Booking confirmed.")
    session.save(update_fields=["status", "summary", "updated_at"])
    _notify_user(session)
    _cancel_siblings(session)


def _do_run(session_id):
    session = NegotiationSession.objects.get(id=session_id)
    if session.status in NegotiationSession.TERMINAL_STATUSES | {"pending_confirmation"}:
        return

    session.status = "contacting" if not session.messages.exists() else "negotiating"
    session.save(update_fields=["status", "updated_at"])

    system = _build_system_prompt(session)

    msgs = list(session.messages.order_by("timestamp").values("direction", "body"))

    if not msgs:
        history = [{"role": "user", "content": (
            "Please introduce yourself to the provider and start arranging the booking "
            "according to the traveller's preferences."
        )}]
    else:
        history = []
        for m in msgs:
            role = "assistant" if m["direction"] == "outbound" else "user"
            history.append({"role": role, "content": m["body"]})
        if history[0]["role"] != "user":
            history.insert(0, {"role": "user", "content": "Continue the negotiation."})

    while True:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=_TOOLS,
            messages=history,
        )

        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break
        if response.stop_reason != "tool_use":
            break

        tool_results = []
        stop = False
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = _execute_tool(session, block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })
            if block.name in ("close_session", "propose_to_user"):
                stop = True

        history.append({"role": "user", "content": tool_results})

        if stop:
            break
