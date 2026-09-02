#!/usr/bin/env python3
"""Build the activity-provider outreach list, with a WhatsApp confirmation link.

Scans content/ for `commercial: true` POIs and writes tools/activity_outreach.csv:
one row per provider, with the contact routes we hold and a per-provider
confirmation code.

Why confirmation works the way it does
--------------------------------------
We only publish a `whatsapp:` number a provider has actually confirmed. The
obvious automation — "put a tracking link in the email, treat a click as
confirmation" — does not work: corporate mail security (Defender, Proofpoint
and friends) fetches every URL in an inbound message to scan it, so links get
clicked by robots before a human ever sees them. That would fill the file with
confirmations nobody made.

Instead the email carries a wa.me link pointing at *our* number with a
prefilled message:

    https://wa.me/<W66_WHATSAPP>?text=CONFIRM%20<code>

Tapping it opens WhatsApp on the provider's own phone with the text ready; they
press send. We then receive a message from their real WhatsApp number
containing their code. One tap proves three things at once — that they use
WhatsApp, which number it is, and that they agreed to be contacted there — and
a link scanner cannot forge it, because scanning a URL does not send a message.

Set W66_WHATSAPP to World66's own WhatsApp number (digits, international, no
plus). Until that exists the script still runs and leaves the link column
templated.

Usage:
    python3 tools/activity_outreach.py            # rewrite the CSV
    python3 tools/activity_outreach.py --emails   # print the mail-merge rows
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import urllib.parse
from pathlib import Path

import frontmatter

REPO = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO / "content"
OUT = REPO / "tools" / "activity_outreach.csv"

W66_WHATSAPP = os.environ.get("W66_WHATSAPP", "").strip()

FIELDS = [
    "town", "poi_path", "provider", "phone", "email", "url",
    "whatsapp", "confirm_code", "confirm_link", "emailed", "confirmed",
]


def confirm_code(poi_path: str) -> str:
    """Short, stable, human-readable code — it gets typed into WhatsApp."""
    parts = [p for p in poi_path.split("/") if p]
    tail = "-".join(parts[-2:])
    return "W66-" + re.sub(r"[^A-Z0-9-]", "", tail.upper().replace("_", "-"))[:28]


def confirm_link(code: str) -> str:
    number = W66_WHATSAPP or "<W66_WHATSAPP>"
    text = urllib.parse.quote(f"CONFIRM {code}")
    return f"https://wa.me/{number}?text={text}"


def providers():
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        try:
            post = frontmatter.load(path)
        except Exception:
            continue
        if not post.metadata.get("commercial"):
            continue
        rel = path.relative_to(CONTENT_DIR).with_suffix("")
        poi_path = str(rel)
        yield {
            "town": rel.parent.name,
            "poi_path": poi_path,
            "provider": post.metadata.get("title", ""),
            "phone": post.metadata.get("phone", ""),
            "email": post.metadata.get("email", ""),
            "url": post.metadata.get("url", ""),
            "whatsapp": post.metadata.get("whatsapp", ""),
        }


def existing_rows() -> dict[str, dict]:
    """Keep emailed/confirmed state across regenerations."""
    if not OUT.is_file():
        return {}
    with OUT.open(encoding="utf-8", newline="") as fh:
        return {r["poi_path"]: r for r in csv.DictReader(fh)}


def build() -> list[dict]:
    prior = existing_rows()
    rows = []
    for p in providers():
        code = confirm_code(p["poi_path"])
        was = prior.get(p["poi_path"], {})
        rows.append({
            **p,
            "confirm_code": code,
            "confirm_link": confirm_link(code),
            "emailed": was.get("emailed", ""),
            # A confirmed number is only ever set by a human who received the
            # provider's WhatsApp message — never derived here.
            "confirmed": was.get("confirmed", ""),
        })
    return rows


EMAIL_TEMPLATE = """To: {email}
Subject: {provider} is listed on World66

Hello,

We've written up {provider} on World66, the open travel guide — the page is
here and free, with no commission and no booking fees:

    https://world66.ai/{poi_path}

Two things:

1. If anything on the page is wrong — prices, season, meeting point — tell us
   and we'll fix it.

2. Do you take bookings on WhatsApp? If so, tap this link and press send:

    {confirm_link}

   That sends us a short message from your WhatsApp, which is how we confirm
   the number before we publish it. We won't add a WhatsApp button until you
   do — we don't want to send travellers to a number you don't watch.

Thanks,
World66
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emails", action="store_true", help="print drafted emails")
    args = ap.parse_args()

    rows = build()
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(REPO)} — {len(rows)} providers, "
          f"{sum(1 for r in rows if r['whatsapp'])} with a confirmed WhatsApp number")
    if not W66_WHATSAPP:
        print("note: W66_WHATSAPP unset, confirm links are templated")

    if args.emails:
        for r in rows:
            if not r["email"]:
                print(f"\n--- {r['provider']}: no email address, needs the web form at {r['url']}")
                continue
            print("\n" + "=" * 72)
            print(EMAIL_TEMPLATE.format(**r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
