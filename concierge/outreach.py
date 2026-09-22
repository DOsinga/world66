"""Turning a chat into enquiries that reach real operators.

The rules that matter are all here rather than in the prompt, because a model
cannot be the thing that decides who gets email:

- the recipient address comes from the operator's own page, never from the
  model, which only ever names a path;
- an operator that has asked to be left alone is dropped before sending;
- nothing is sent until the traveller has proved their own address;
- the envelope — subject, the line explaining why they are hearing from us,
  the opt-out — is templated, and the model writes only the middle.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core import signing

from guide.models import load_page

MAX_PROVIDERS = 5
DRAFT_SALT = "concierge-draft"
CONFIRM_SALT = "concierge-confirm"
OPTOUT_SALT = "concierge-optout"
DRAFT_MAX_AGE = 60 * 60 * 6
CONFIRM_MAX_AGE = 60 * 60 * 24
MAX_SUBJECT = 120
MAX_BODY = 2500
MAX_NAME = 80

EMAIL_RE = re.compile(r"^[^@\s]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def ledger_path():
    """Where sends are recorded.

    Not `outreach/log.csv`: that file is version-controlled and would be
    clobbered by the next deploy. This one lives beside the checkout.
    """
    return Path(os.environ.get(
        "CONCIERGE_LEDGER", str(Path(settings.BASE_DIR) / "outreach" / "enquiries.jsonl")
    ))


def valid_email(value):
    return bool(EMAIL_RE.match(str(value or "").strip()))


def provider_email(page):
    raw = str(page.meta.get("email") or "").strip()
    return raw if valid_email(raw) else ""


def accepts_enquiries(page):
    return not page.meta.get("no_enquiries")


def resolve_providers(paths):
    """Return (sendable pages, reasons for everything dropped)."""
    keep, dropped = [], []
    seen = set()
    for raw in list(paths or [])[: MAX_PROVIDERS * 3]:
        path = str(raw or "").strip().strip("/")
        if not path or ".." in path.split("/") or path in seen:
            continue
        seen.add(path)
        page = load_page(path)
        if not page or page.page_type != "poi" or not page.is_commercial:
            dropped.append(f"{path}: not an operator in the guide")
            continue
        if not accepts_enquiries(page):
            dropped.append(f"{page.title}: has asked not to receive enquiries")
            continue
        if not provider_email(page):
            dropped.append(f"{page.title}: publishes no email address")
            continue
        keep.append(page)
        if len(keep) >= MAX_PROVIDERS:
            break
    return keep, dropped


def sign_draft(draft):
    return signing.dumps(draft, salt=DRAFT_SALT)


def load_draft(token):
    try:
        draft = signing.loads(str(token or ""), salt=DRAFT_SALT, max_age=DRAFT_MAX_AGE)
    except signing.BadSignature:
        return None
    return draft if isinstance(draft, dict) else None


def sign_confirmation(payload):
    return signing.dumps(payload, salt=CONFIRM_SALT)


def load_confirmation(token):
    try:
        payload = signing.loads(str(token or ""), salt=CONFIRM_SALT, max_age=CONFIRM_MAX_AGE)
    except signing.BadSignature:
        return None
    return payload if isinstance(payload, dict) else None


def confirmation_id(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()[:32]


def already_sent(token):
    """A confirmation link works once; the ledger is what remembers that."""
    wanted = confirmation_id(token)
    path = ledger_path()
    if not path.is_file():
        return False
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if wanted in line:
                    return True
    except OSError:
        return False
    return False


def record(entry):
    path = ledger_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        pass


def build_enquiry(provider, draft, traveller, page_url, optout_url):
    """The message an operator receives. The model wrote only `draft['message']`."""
    subject = str(draft.get("subject") or "").strip()[:MAX_SUBJECT] or (
        f"Enquiry from a World66 traveller"
    )
    message = str(draft.get("message") or "").strip()[:MAX_BODY]
    name = str(traveller.get("name") or "").strip()[:MAX_NAME] or "a traveller"
    email = traveller.get("email", "")
    lines = [
        f"Hello {provider.title},",
        "",
        f"{name} is planning a trip and found you on World66. Their enquiry is "
        "below, and their address is on the reply-to of this mail — replying "
        "goes straight to them, not to us.",
        "",
        message,
        "",
        "--",
        f"Sent by the World66 concierge for {name} <{email}>.",
        "World66 is a free travel guide. Your listing is editorial, it costs "
        "nothing, and we take no commission on anything you arrange.",
        f"Your page: {page_url}",
        f"No more enquiries like this: {optout_url}",
    ]
    return subject, "\n".join(lines)


def build_confirmation(draft, providers, traveller, confirm_url):
    """The mail the traveller gets. Clicking through is what releases the rest."""
    name = str(traveller.get("name") or "").strip()[:MAX_NAME] or "there"
    listed = "\n".join(f"  - {p.title}" for p in providers)
    lines = [
        f"Hi {name},",
        "",
        "You asked the World66 concierge to send your enquiry to these operators:",
        "",
        listed,
        "",
        "Nothing has gone to them yet. Open this link and confirm, and we'll "
        "send it — they will reply to you directly at this address.",
        "",
        confirm_url,
        "",
        "If you didn't ask for this, ignore this mail and nothing happens. "
        "The link stops working after a day.",
        "",
        "--",
        "World66 — a free travel guide. We take no commission on anything you book.",
    ]
    return "Confirm your enquiry — World66 concierge", "\n".join(lines)


def ledger_entry(provider, traveller, draft, token, message_id):
    return {
        "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "confirmation": confirmation_id(token),
        "provider": provider.title,
        "provider_path": provider.path,
        "provider_email": provider_email(provider),
        "outreach_code": provider.outreach_code,
        "traveller_email": traveller.get("email", ""),
        "subject": str(draft.get("subject") or "")[:MAX_SUBJECT],
        "message_id": message_id,
        "ts": int(time.time()),
    }
