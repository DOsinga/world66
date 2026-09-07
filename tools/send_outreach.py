#!/usr/bin/env python3
"""Turn the outreach drafts into Gmail drafts, with their QR code attached.

This creates drafts. It cannot send: the only scope requested is
``gmail.compose``, which Google does not permit to send mail. You review each
one in Gmail and press send yourself. That is deliberate — these go to real
businesses who did not ask to hear from us, and a script should not be the last
thing between a template and forty strangers.

Setup, once:

  1. console.cloud.google.com, signed in as the account that will send
  2. enable the Gmail API
  3. OAuth consent screen: Internal if the project is in a Workspace org,
     otherwise External kept in Testing with your own address as a test user
  4. add the scope https://www.googleapis.com/auth/gmail.compose
  5. Credentials -> OAuth client ID -> Desktop app -> download the JSON to
     ~/.config/world66/gmail_client_secret.json
  6. pip install google-api-python-client google-auth-oauthlib

Usage:
    python3 tools/send_outreach.py --dry-run              # parse and report, touch nothing
    python3 tools/send_outreach.py --only 592_tours       # one, to see how it looks
    python3 tools/send_outreach.py                        # the rest

Every draft created is recorded in build/outreach_ledger.json, and a provider
already in the ledger is skipped, so a rerun after an interruption does not
leave two drafts for the same company. --force overrides that.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import time
from base64 import urlsafe_b64encode
from email.message import EmailMessage
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DRAFT_DIR = REPO / "build" / "provider_emails"
QR_DIR = REPO / "build" / "provider_qr"
LEDGER = REPO / "build" / "outreach_ledger.json"

CONFIG_DIR = Path.home() / ".config" / "world66"
CLIENT_SECRET = CONFIG_DIR / "gmail_client_secret.json"
TOKEN = CONFIG_DIR / "gmail_token.json"

# compose, not send. See the module docstring.
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

ATTACH_RE = re.compile(r"^\[attach:\s*(.+?)\s*\]\s*$", re.M)


def parse_draft(path):
    """Split one draft file into recipient, subject, body and attachment name."""
    text = path.read_text(encoding="utf-8")
    attachment = ""
    match = ATTACH_RE.search(text)
    if match:
        attachment = match.group(1)
        text = ATTACH_RE.sub("", text)

    header, _, body = text.partition("\n\n")
    fields = {}
    for line in header.split("\n"):
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"{path.name}: header line without a colon: {line!r}")
        fields[key.strip().lower()] = value.strip()

    missing = [k for k in ("to", "subject") if not fields.get(k)]
    if missing:
        raise ValueError(f"{path.name}: no {', '.join(missing)} header")

    return {
        "slug": path.stem,
        "to": fields["to"],
        "subject": fields["subject"],
        "body": body.strip() + "\n",
        "attachment": attachment,
    }


def build_message(draft, sender, qr_dir):
    msg = EmailMessage()
    msg["To"] = draft["to"]
    msg["Subject"] = draft["subject"]
    if sender:
        msg["From"] = sender
    msg.set_content(draft["body"])

    if draft["attachment"]:
        qr = qr_dir / draft["attachment"]
        if not qr.is_file():
            raise FileNotFoundError(f'{draft["slug"]}: {qr} is missing (run --qr)')
        ctype, _ = mimetypes.guess_type(qr.name)
        maintype, _, subtype = (ctype or "application/octet-stream").partition("/")
        msg.add_attachment(qr.read_bytes(), maintype=maintype, subtype=subtype,
                           filename=qr.name)
    return msg


def gmail_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit("pip install google-api-python-client google-auth-oauthlib")

    creds = None
    if TOKEN.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.is_file():
                sys.exit(f"no OAuth client at {CLIENT_SECRET} — see the docstring")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
        TOKEN.chmod(0o600)
    return build("gmail", "v1", credentials=creds)


def load_ledger():
    if LEDGER.is_file():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {}


def save_ledger(ledger):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", default=str(DRAFT_DIR), help="where the .txt drafts live")
    ap.add_argument("--qr-dir", default=str(QR_DIR), help="where the QR PNGs live")
    ap.add_argument("--only", default="", help="slug fragment: do just these")
    ap.add_argument("--limit", type=int, default=0, help="stop after N")
    ap.add_argument("--sender", default="", help="From address, if not the account default")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between API calls")
    ap.add_argument("--force", action="store_true", help="redo providers already in the ledger")
    ap.add_argument("--dry-run", action="store_true", help="parse and report, create nothing")
    args = ap.parse_args()

    draft_dir, qr_dir = Path(args.drafts), Path(args.qr_dir)
    files = sorted(draft_dir.glob("*.txt"))
    if not files:
        sys.exit(f"no drafts in {draft_dir} — run tools/provider_qr.py --emails --qr")
    if args.only:
        files = [f for f in files if args.only in f.stem]
        if not files:
            sys.exit(f"no draft matching {args.only!r}")

    ledger = load_ledger()
    queue = []
    for path in files:
        draft = parse_draft(path)
        if draft["slug"] in ledger and not args.force:
            continue
        build_message(draft, args.sender, qr_dir)   # fail now, not mid-run
        queue.append(draft)
    if args.limit:
        queue = queue[: args.limit]

    skipped = len(files) - len(queue)
    print(f"{len(queue)} to create, {skipped} already in the ledger or over the limit")
    if args.dry_run:
        for d in queue:
            print(f"  {d['to']:38} {d['subject']}")
        return 0
    if not queue:
        return 0

    service = gmail_service()
    for i, draft in enumerate(queue, 1):
        msg = build_message(draft, args.sender, qr_dir)
        raw = urlsafe_b64encode(msg.as_bytes()).decode()
        created = service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()
        ledger[draft["slug"]] = {"draft_id": created["id"], "to": draft["to"]}
        save_ledger(ledger)   # after each one: an interruption must not lose the record
        print(f"  [{i}/{len(queue)}] draft for {draft['to']}")
        if args.delay and i < len(queue):
            time.sleep(args.delay)

    print(f"\n{len(queue)} draft(s) in Gmail. Review them there and send yourself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
