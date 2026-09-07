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
    python3 tools/provider_qr.py --emails          # write the outreach emails
    python3 tools/provider_qr.py --assign --qr --emails

    --out DIR     where QR files go (default: build/provider_qr, gitignored)
    --base URL    site root for the links (default: https://world66.ai)
    --country X   limit to a content path fragment, e.g. --country suriname
"""

from __future__ import annotations

import argparse
import hashlib
import random
import re
import string
import sys
import textwrap
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


# Which second language a country's providers read. English goes first in every
# mail; this is what follows the rule under it. Guyana is English-speaking, so
# it gets nothing extra rather than a translation nobody needs.
LANG_BY_PATH = {
    "/france/": "fr",
    "/suriname/": "nl",
}


def language_for(rel):
    for fragment, lang in LANG_BY_PATH.items():
        if fragment in f"/{rel}/":
            return lang
    return ""


HEADER = """To: {email}
Subject: {title} is listed on World66 — your own link and QR code

"""

BODY = {
    "en": """Hello,

We are building a travel guide that helps travellers plan their trip on the go
using WhatsApp, and we have just added {title}. Being in our guide is free, we
take no commission, and there is nothing to sign up for. Please check out the
link:

{link}

Three things that would help:

1. Put a link on your website or your social profiles, so people can find the
   wider guide to {location_name} from you.

2. The attached QR code goes to the same place. It prints cleanly at any size,
   so it works on a card at reception, a sign on the boat, or the back of a
   receipt.

3. If you have any comments on the {location_name} guide, shoot us an email and
   we'll update it. We strive to be the best travel guide in the world and we
   need all the help we can get!
""",

    "nl": """Beste,

Wij bouwen een reisgids die reizigers helpt hun reis onderweg te plannen via
WhatsApp, en we hebben zojuist {title} toegevoegd. Vermelding in onze gids is
gratis, we vragen geen commissie en u hoeft zich nergens voor aan te melden.
Kijkt u vooral even:

{link}

Drie dingen die zouden helpen:

1. Zet een link op uw website of op uw social media, zodat mensen via u de rest
   van de gids over {location_name} kunnen vinden.

2. De bijgevoegde QR-code gaat naar dezelfde plek. Hij drukt scherp af op elk
   formaat, dus hij werkt op een kaartje bij de balie, een bordje op de boot of
   achterop een bonnetje.

3. Hebt u opmerkingen over de gids over {location_name}, stuur ons dan een
   e-mail en we passen het aan. We willen de beste reisgids ter wereld maken en
   kunnen alle hulp gebruiken!
""",

    "fr": """Bonjour,

Nous construisons un guide de voyage qui aide les voyageurs à organiser leur
séjour en cours de route, via WhatsApp, et nous venons d'y ajouter {title}.
Y figurer est gratuit, nous ne prenons aucune commission et il n'y a aucune
inscription. Jetez-y un œil :

{link}

Trois choses qui nous aideraient :

1. Mettez un lien sur votre site ou vos réseaux sociaux, pour que vos visiteurs
   découvrent depuis chez vous le reste de notre guide « {location_name} ».

2. Le QR code joint mène au même endroit. Il s'imprime nettement à n'importe
   quelle taille : sur une carte à l'accueil, un panneau sur le bateau ou au dos
   d'un reçu.

3. Si vous avez des remarques sur notre guide « {location_name} », écrivez-nous
   et nous le mettrons à jour. Nous voulons faire le meilleur guide de voyage du
   monde, et toute aide est la bienvenue !
""",
}

SIGNOFF = {
    "en": "Thanks,\nRichard & the World66 team",
    "nl": "Groeten,\nRichard en het World66-team",
    "fr": "Merci,\nRichard et l'équipe World66",
}

# The line between the two halves, so the reader can see at a glance that the
# second block is the same mail and not a second request.
DIVIDER = {
    "nl": "\n--- Dezelfde tekst in het Nederlands ---\n\n",
    "fr": "\n--- Le même message en français ---\n\n",
}



def wrap(text, width=78):
    """Re-flow paragraphs after substitution. Indented lines (the URLs) are left
    alone, and numbered items keep their hanging indent."""
    out = []
    for block in text.split("\n\n"):
        lines = block.split("\n")
        # The link sits flush left on its own line now, so it has to be exempt
        # from re-flowing as well as anything indented.
        if any(line.startswith("    ") for line in lines) or (
            len(lines) == 1 and lines[0].startswith("http")
        ):
            out.append(block)
            continue
        joined = " ".join(line.strip() for line in lines if line.strip())
        if not joined:
            out.append(block)
            continue
        indent = "   " if re.match(r"^\d+\.\s", joined) else ""
        out.append(textwrap.fill(joined, width=width, subsequent_indent=indent,
                                 break_long_words=False, break_on_hyphens=False))
    return "\n\n".join(out)


def compose(row):
    """English first, then the same mail in the local language where there is one."""
    fields = {
        "email": row["email"], "title": row["title"], "page_url": row["page_url"],
        "link": row["link"], "location_name": row["location_name"],
    }
    def half(lang):
        return f'{wrap(BODY[lang].format(**fields))}\n\n{SIGNOFF[lang]}\n'

    text = HEADER.format(**fields) + half("en")
    lang = row["lang"]
    if lang and lang in BODY:
        text += DIVIDER[lang] + half(lang)
    return text


def location_name(location_rel):
    """The location's own title — 'Saint-Valery-sur-Somme', not 'St Valery Sur Somme'."""
    md = CONTENT_DIR / f"{location_rel}.md"
    if md.is_file():
        try:
            title = frontmatter.load(md).metadata.get("title")
            if title:
                return str(title)
        except Exception:
            pass
    return location_rel.rsplit("/", 1)[-1].replace("_", " ").title()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assign", action="store_true", help="assign codes where missing")
    ap.add_argument("--qr", action="store_true", help="write QR PNG and SVG files")
    ap.add_argument("--emails", action="store_true", help="write the outreach emails")
    ap.add_argument("--print", action="store_true", help="also print each draft to stdout")
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
        loc = location_of(rel)
        rows.append({
            "rel": rel,
            "code": code,
            "title": post.metadata.get("title", rel),
            "email": post.metadata.get("email", ""),
            "url": post.metadata.get("url", ""),
            "location": loc,
            "location_name": location_name(loc),
            "lang": language_for(rel),
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
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        no_email = [r for r in rows if not r["email"]]
        written = 0
        for r in rows:
            if not r["email"]:
                continue
            text = compose(r) + f"\n[attach: {r['slug']}-{r['code']}.png]\n"
            draft = out / f'{r["slug"]}-{r["code"]}.txt'
            draft.write_text(text, encoding="utf-8")
            written += 1
            if args.print:
                print("\n" + "=" * 72)
                print(text)
        by_lang = {}
        for r in rows:
            if r["email"]:
                by_lang[r["lang"] or "en only"] = by_lang.get(r["lang"] or "en only", 0) + 1
        print(f"wrote {written} draft{'s' if written != 1 else ''} to {out}"
              f"  ({', '.join(f'{k}: {v}' for k, v in sorted(by_lang.items()))})")
        if no_email:
            print(f"\n{len(no_email)} provider(s) publish no email address — "
                  f"contact them through their website instead:")
            for r in no_email:
                print(f"  {r['title']}  {r['url'] or '(no website either)'}  -> {r['link']}")

    print(f"\n{len(rows)} provider{'s' if len(rows) != 1 else ''} with codes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
