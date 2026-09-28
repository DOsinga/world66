"""The concierge agent.

A traveller chats; the agent asks the questions a good guide would ask, looks
the answers up in World66's own content, writes a brief they can correct, and
drafts the enquiry that goes to the operators. The agent never sends anything
itself: it hands a signed draft to the browser, and the traveller confirms by
email before a single message leaves. See `outreach.py`.

There is no database: like the rest of the site, this reads the filesystem and
`search.db`, and the conversation itself lives in the browser and is posted
back with each turn.
"""

import json
import os

from django.conf import settings

from guide.models import CONTENT_DIR, build_city_tag_index, find_tagged_pois, load_page

from . import outreach

MODEL = os.environ.get("CONCIERGE_MODEL", "claude-sonnet-5")
MAX_TOKENS = 700
MAX_TOOL_ROUNDS = 6

# What the traveller is told, in the panel and again in the prompt. The guide
# takes no commission and sells nothing, and an assistant that let someone
# believe otherwise would be trading on that reputation.
DISCLOSURE = (
    "I'm an AI assistant for World66. Tell me what you want to do and I'll "
    "find the operators who run it, from the guide's own free pages — no paid "
    "placement, no commission — and send them your enquiry, so they can reply "
    "to you direct."
)

SYSTEM_PROMPT = f"""You are the World66 concierge, a chat assistant on the World66 travel guide.

Who you are, and what you say if asked:
{DISCLOSURE}

Your job is to get from a vague wish to something bookable: a named operator
or place from the guide, and the next step to take. Work towards that from the
first message.

How to write. You are in a small chat window, not writing an email.
- Keep every reply under 60 words. Two or three sentences is normal.
- Ask ONE question at a time. Never a numbered list of questions.
- No preamble, no praise, no restating what they just told you. No sign-off.
- Don't narrate what you are about to look up — look it up and answer.
- Markdown renders here: **bold** and `- ` bullets. At most three bullets, one
  line each.

Ground every suggestion in the guide:
- `search_guide` finds pages across the whole site.
- `list_providers` lists the bookable operators on a destination page.
- `read_page` returns a page in full, including an operator's own published
  contact details.

Rules:
- Only name places and operators you have actually read in the guide. If the
  guide doesn't cover somewhere, say so plainly — do not fill the gap from
  memory, and never invent a phone number, an email address or a price.
- Quote prices only as the page states them, and say they may have changed.
- Recommendations come from the guide's own editorial judgement, not from
  anybody paying us. Say so if it comes up.
- The traveller books direct with the operator: we pass the enquiry on, they
  reply to the traveller, and the arrangement is between the two of them.
  Never say you have booked, reserved, held or paid for anything.
- Link to pages as plain paths, like /southamerica/peru/cusco, and do not
  invent paths — use the ones the tools return.
- Call `save_brief` as soon as you have a destination, a rough when, a group
  size and one candidate from the guide. Don't hold out for every detail.
- The brief appears on screen as a card. Never repeat its contents in your
  message — one short line asking what to fix is enough.

Getting in touch:
- When the traveller wants to approach an operator, call `draft_enquiry`. Write
  the message in their voice, first person, with the facts an operator needs to
  quote: dates, numbers, what they want, anything that rules an option out.
- The draft appears on screen with a form for their name and address. Say in
  one line that they review it there and confirm by email; do not repeat the
  draft in your message.
- Never say the enquiry has been sent. You have not sent it and cannot: it
  goes out only after they confirm by email.
- Five operators is the limit, and only ones that publish an address in the
  guide. If one is dropped, say so plainly and offer another.
"""

TOOLS = [
    {
        "name": "search_guide",
        "description": (
            "Full-text search across World66. Returns matching pages with "
            "their titles, paths and types."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search words, e.g. 'Cusco trekking'."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_providers",
        "description": (
            "List the bookable activity providers on a destination, with what "
            "they sell and how to reach them. Takes the destination's path, "
            "e.g. 'southamerica/peru/cusco'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Destination path, no leading slash."},
                "kind": {
                    "type": "string",
                    "description": "Optional activity kind to filter on, e.g. 'diving'.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_page",
        "description": "Return one World66 page: its text, and its practical details if it has any.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Page path, no leading slash."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "draft_enquiry",
        "description": (
            "Write the enquiry the traveller will send to operators, and show "
            "it to them for approval. Call this once they have said they want "
            "to get in touch. Nothing is sent by this tool: the traveller "
            "reviews it, gives their name and address, and confirms by email. "
            "Name at most five operators, all from the guide."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "providers": {
                    "type": "array",
                    "description": "Paths of the operators to approach, as the tools returned them.",
                    "items": {"type": "string"},
                },
                "subject": {
                    "type": "string",
                    "description": "Subject line, e.g. 'Upper Suriname River, 12-15 July, two people'.",
                },
                "message": {
                    "type": "string",
                    "description": (
                        "The enquiry itself, written as the traveller: what "
                        "they want, when, how many, and what they need to know "
                        "to decide. No greeting and no sign-off — those are "
                        "added around it."
                    ),
                },
            },
            "required": ["providers", "subject", "message"],
        },
    },
    {
        "name": "save_brief",
        "description": (
            "Write up what the traveller wants, so they can see it and correct "
            "it. Call this once you have the essentials."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "dates": {"type": "string", "description": "Dates or 'flexible, roughly ...'."},
                "group": {"type": "string", "description": "How many people, and who."},
                "budget": {"type": "string"},
                "interests": {"type": "string", "description": "What they want out of it."},
                "candidates": {
                    "type": "array",
                    "description": "Providers or places from the guide worth approaching.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "path": {"type": "string"},
                            "why": {"type": "string"},
                        },
                        "required": ["title", "path"],
                    },
                },
                "notes": {"type": "string", "description": "Anything else worth stating."},
            },
            "required": ["destination", "interests"],
        },
    },
]

PROVIDER_FIELDS = ("address", "phone", "email", "url", "price", "opening_hours")


def _clean_path(raw):
    """Normalise a model-supplied path, and refuse anything that leaves content/."""
    path = str(raw or "").strip().strip("/")
    if not path or ".." in path.split("/"):
        return ""
    return path


def _provider_summary(poi):
    out = {
        "title": poi.title,
        "path": poi.path,
        "activity": poi.activity_label,
        "snippet": poi.meta.get("snippet", ""),
    }
    for field in PROVIDER_FIELDS:
        value = poi.meta.get(field)
        if value:
            out[field] = str(value)
    if poi.whatsapp_link:
        out["whatsapp"] = str(poi.meta.get("whatsapp", ""))
    return out


def tool_search_guide(query):
    from guide.views import _search_results

    results = _search_results(str(query or "")[:120])[:12]
    if not results:
        return "No pages matched. Try fewer or different words."
    return json.dumps([
        {"title": r["title"], "path": r["url"].lstrip("/"),
         "type": r["page_type"], "location": r["location"]}
        for r in results
    ])


def tool_list_providers(path, kind=""):
    path = _clean_path(path)
    if not path or not (CONTENT_DIR / path).is_dir():
        return "No such destination in the guide."
    index = build_city_tag_index(path)
    providers = [p for p in find_tagged_pois(path, "activities", index) if p.is_commercial]
    if kind:
        providers = [p for p in providers if p.activity_kind == kind]
    if not providers:
        return "The guide lists no bookable operators here yet."
    return json.dumps([_provider_summary(p) for p in providers[:25]])


def tool_read_page(path):
    path = _clean_path(path)
    page = load_page(path) if path else None
    if not page:
        return "No such page in the guide."
    out = {
        "title": page.title,
        "path": page.path,
        "type": page.page_type,
        "snippet": page.meta.get("snippet", ""),
        "text": page.body[:5000],
    }
    if page.page_type == "poi":
        out.update({k: v for k, v in _provider_summary(page).items() if k in PROVIDER_FIELDS})
    return json.dumps(out)


def _normalise_brief(brief):
    """Keep only the fields we render, and only paths that really exist."""
    out = {k: str(brief.get(k, "") or "") for k in
           ("destination", "dates", "group", "budget", "interests", "notes")}
    candidates = []
    for item in brief.get("candidates") or []:
        if not isinstance(item, dict):
            continue
        path = _clean_path(item.get("path"))
        page = load_page(path) if path else None
        if not page:
            continue
        candidates.append({
            "title": page.title,
            "path": page.path,
            "why": str(item.get("why", "") or ""),
        })
    out["candidates"] = candidates[:8]
    return out


def _build_draft(tool_input):
    """Check the operators the model named, and sign what it wrote.

    Signing here is what stops the enquiry being edited on its way to the send
    endpoint: the browser holds the token, not the text.
    """
    providers, dropped = outreach.resolve_providers(tool_input.get("providers"))
    if not providers:
        reasons = "; ".join(dropped) or "none of those are operators in the guide"
        return None, f"Nothing to send: {reasons}. Suggest other operators."

    draft = {
        "subject": str(tool_input.get("subject") or "").strip()[:outreach.MAX_SUBJECT],
        "message": str(tool_input.get("message") or "").strip()[:outreach.MAX_BODY],
        "providers": [p.path for p in providers],
    }
    card = {
        "subject": draft["subject"],
        "message": draft["message"],
        "token": outreach.sign_draft(draft),
        "providers": [
            {"title": p.title, "path": p.path, "email": outreach.provider_email(p)}
            for p in providers
        ],
        "dropped": dropped,
    }
    note = ""
    if dropped:
        note = " Left out: " + "; ".join(dropped) + "."
    return card, (
        "Draft shown to the traveller with a form for their name and address. "
        "They confirm by email before anything is sent — tell them that, briefly."
        + note
    )


def run_tool(name, tool_input):
    """Run one tool. Returns (text_for_the_model, extras_for_the_browser)."""
    if name == "search_guide":
        return tool_search_guide(tool_input.get("query", "")), {}
    if name == "list_providers":
        return tool_list_providers(tool_input.get("path", ""), tool_input.get("kind", "")), {}
    if name == "read_page":
        return tool_read_page(tool_input.get("path", "")), {}
    if name == "draft_enquiry":
        card, message = _build_draft(tool_input)
        return message, ({"draft": card} if card else {})
    if name == "save_brief":
        brief = _normalise_brief(tool_input)
        dropped = len(tool_input.get("candidates") or []) - len(brief["candidates"])
        note = (
            f" {dropped} suggested page(s) were dropped because they are not in the guide; "
            "do not mention them." if dropped > 0 else ""
        )
        return ("Brief saved and shown to the traveller. Ask them to correct "
                "anything that is wrong." + note), {"brief": brief}
    return f"Unknown tool: {name}", {}


def is_configured():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _page_context(path):
    page = load_page(_clean_path(path)) if path else None
    if not page:
        return ""
    return (
        f"\nThe traveller is reading /{page.path} — {page.title} "
        f"({page.page_type}). Assume that is what they mean unless they say otherwise."
    )


def reply(history, page_path=""):
    """Run the agent over `history` and return (reply_text, extras).

    `history` is a list of {"role": "user"|"assistant", "content": str}.
    `extras` carries what the browser has to render: the brief, and the
    enquiry draft when the agent wrote one.
    """
    import anthropic

    client = anthropic.Anthropic()
    messages = [dict(m) for m in history]
    system = SYSTEM_PROMPT + _page_context(page_path)
    extras = {}
    text_parts = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=getattr(settings, "CONCIERGE_MODEL", MODEL),
            max_tokens=MAX_TOKENS,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        for block in response.content:
            if block.type == "text" and block.text.strip():
                text_parts.append(block.text.strip())
        if response.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result, produced = run_tool(block.name, block.input or {})
            extras.update(produced)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })
        messages.append({"role": "user", "content": results})

    return "\n\n".join(text_parts), extras
