#!/usr/bin/env python3
"""Provider outreach: highlight codes, QR codes and the emails that carry them.

Each bookable provider gets a short code stored in its own frontmatter as
`outreach_code`. A link carrying it — /europe/france/nord/wissant?p=AB12CD —
highlights that provider on the page and hides their direct competitors, so a
customer arriving from the provider's own site or a printed QR sees them first
rather than whoever happens to score highest.

The code lives in frontmatter rather than being derived from the content path.
These codes end up printed on paper and pasted into other people's websites; a
path-derived code would break the first time a page moved, and this repo
restructures content regularly.

Usage:
    python3 tools/provider_qr.py --assign          # give codes to providers lacking one
    python3 tools/provider_qr.py --qr              # write QR PNG + SVG per provider
    python3 tools/provider_qr.py --emails          # print the outreach emails
    python3 tools/provider_qr.py --assign --qr --emails

    --out DIR     where QR files go (default: build/provider_qr, gitignored)
    --base URL    site root for the links (default: https://world66.ai)
    --country X   limit to a content path fragment, e.g. --country suriname
"""

from __future__ import annotations

import argparse
import hashlib
import random
import string
import sys
from pathlib import Path

import frontmatter

REPO = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO / "content"
DEFAULT_OUT = REPO / "build" / "provider_qr"
DEFAULT_BASE = "https://world66.ai"

# No vowels and no 0/O/1/I: these get read aloud and typed by hand off paper.
ALPHABET = "23456789BCDFGHJKLMNPQRSTVWXYZ"
CODE_LEN = 6


def providers(fragment=""):
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        rel = str(path.relative_to(CONTENT_DIR).with_suffix(""))
        if fragment and fragment not in rel:
            continue
        try:
            post = frontmatter.load(path)
        except Exception:
            continue
        if post.metadata.get("commercial"):
            yield path, rel, post


def existing_codes():
    return {
        str(post.metadata.get("outreach_code") or "").upper()
        for _, _, post in providers()
        if post.metadata.get("outreach_code")
    }


def make_code(seed, taken):
    """Deterministic first, then random — so a rerun is stable but collisions resolve."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    code = "".join(ALPHABET[b % len(ALPHABET)] for b in digest[:CODE_LEN])
    while code in taken:
        code = "".join(random.choice(ALPHABET) for _ in range(CODE_LEN))
    return code


def location_of(rel):
    """The page a provider's link should point at: the location it sits under."""
    return rel.rsplit("/", 1)[0]


def link_for(base, rel, code):
    return f"{base.rstrip('/')}/{location_of(rel)}?p={code}"


EMAIL = """To: {email}
Subject: {title} is listed on World66 — your own link and QR code

Hello,

{title} has a page on World66, the open travel guide. It is free, we take no
commission, and there is nothing to sign up for:

    {page_url}

We have also made you your own link:

    {link}

Anyone opening it lands on the {location_name} page with {title} shown first,
and your direct competitors hidden. It is the same page — just yours at the
front of it.

Two things that would help, if you think it is worth it:

1. Put the link on your website or your social profiles, so people can find
   the wider guide to {location_name} from you.

2. The attached QR code goes to the same place. It prints cleanly at any size,
   so it works on a card at reception, a sign on the boat, or the back of a
   receipt.

If anything on your page is wrong — prices, season, meeting point, the phone
number — reply and we will fix it. If you would rather not be listed at all,
say so and we will take the page down.

Thanks,
World66
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assign", action="store_true", help="assign codes where missing")
    ap.add_argument("--qr", action="store_true", help="write QR PNG and SVG files")
    ap.add_argument("--emails", action="store_true", help="print outreach emails")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--country", default="", help="limit to a content path fragment")
    args = ap.parse_args()

    if not (args.assign or args.qr or args.emails):
        ap.error("nothing to do — pass --assign, --qr and/or --emails")

    if args.assign:
        taken = existing_codes()
        n = 0
        for path, rel, post in providers(args.country):
            if post.metadata.get("outreach_code"):
                continue
            code = make_code(rel, taken)
            taken.add(code)
            post["outreach_code"] = code
            path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
            n += 1
            print(f"  assigned {code}  {rel}")
        print(f"assigned {n} new code{'s' if n != 1 else ''}")

    rows = []
    for path, rel, post in providers(args.country):
        code = str(post.metadata.get("outreach_code") or "").upper()
        if not code:
            print(f"  no code yet, skipping: {rel} (run --assign)", file=sys.stderr)
            continue
        rows.append({
            "rel": rel,
            "code": code,
            "title": post.metadata.get("title", rel),
            "email": post.metadata.get("email", ""),
            "url": post.metadata.get("url", ""),
            "location": location_of(rel),
            "link": link_for(args.base, rel, code),
            "page_url": f"{args.base.rstrip('/')}/{rel}",
            "slug": rel.rsplit("/", 1)[-1],
        })

    if args.qr:
        try:
            import segno
        except ImportError:
            sys.exit("segno is not installed — pip install segno (it is in requirements.in)")
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for r in rows:
            qr = segno.make(r["link"], error="h")   # h: survives a logo or a coffee ring
            qr.save(out / f'{r["slug"]}-{r["code"]}.png', scale=8, border=2)
            qr.save(out / f'{r["slug"]}-{r["code"]}.svg', scale=8, border=2)
        print(f"wrote {len(rows) * 2} QR files to {out}")

    if args.emails:
        no_email = [r for r in rows if not r["email"]]
        for r in rows:
            if not r["email"]:
                continue
            print("\n" + "=" * 72)
            print(EMAIL.format(
                email=r["email"], title=r["title"], page_url=r["page_url"],
                link=r["link"],
                location_name=r["location"].rsplit("/", 1)[-1].replace("_", " ").title(),
            ))
            print(f"[attach: {r['slug']}-{r['code']}.png]")
        if no_email:
            print("\n" + "=" * 72)
            print(f"{len(no_email)} provider(s) publish no email address — "
                  f"contact them through their website instead:")
            for r in no_email:
                print(f"  {r['title']}  {r['url'] or '(no website either)'}  -> {r['link']}")

    print(f"\n{len(rows)} provider{'s' if len(rows) != 1 else ''} with codes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
