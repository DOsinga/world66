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
import unicodedata
import urllib.parse
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



def country_of(rel):
    parts = rel.split("/")
    return parts[1].replace("_", " ").title() if len(parts) > 1 else "?"


def gmail_url(row, account=None):
    """A Gmail compose window, pre-filled. No credentials, no API, no setup —
    it just opens in whatever account the browser is already signed in to.
    The one thing it cannot do is attach a file, which is why the QR sits on
    the index page ready to paste."""
    prefix = f"https://mail.google.com/mail/u/{account}/" if account is not None \
        else "https://mail.google.com/mail/"
    query = urllib.parse.urlencode({
        "view": "cm", "fs": "1", "tf": "1",
        "to": row["email"], "su": row["subject"], "body": row["body"],
    }, quote_via=urllib.parse.quote)
    return f"{prefix}?{query}"


INDEX_HEAD = """<!doctype html>
<meta charset="utf-8">
<title>World66 provider outreach</title>
<style>
 :root { color-scheme: light dark; --line: #d9d4cc; --ink: #24211d; --dim: #6d675f;
         --paper: #fbf9f5; --accent: #1a6b52; }
 @media (prefers-color-scheme: dark) {
   :root { --line: #38342e; --ink: #ece7df; --dim: #97907f; --paper: #171512;
           --accent: #58c79e; } }
 body { background: var(--paper); color: var(--ink); margin: 0 auto; padding: 32px 20px 80px;
        max-width: 940px; font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
 h1 { font-size: 22px; margin: 0 0 4px; }
 .lede { color: var(--dim); margin: 0 0 28px; max-width: 62ch; }
 h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .09em; color: var(--dim);
      margin: 32px 0 10px; border-bottom: 1px solid var(--line); padding-bottom: 6px; }
 .row { display: grid; grid-template-columns: 72px 1fr auto; gap: 16px; align-items: center;
        padding: 12px 10px; border-bottom: 1px solid var(--line); border-radius: 6px; }
 .row.done { opacity: .42; }
 .row img { width: 72px; height: 72px; image-rendering: pixelated; background: #fff;
            border-radius: 4px; padding: 3px; cursor: pointer; }
 .name { font-weight: 600; }
 .meta { color: var(--dim); font-size: 13px; }
 .lang { display: inline-block; font-size: 11px; letter-spacing: .06em; text-transform: uppercase;
         border: 1px solid var(--line); border-radius: 3px; padding: 1px 5px; margin-left: 7px;
         color: var(--dim); }
 .go { display: inline-block; background: var(--accent); color: #fff; text-decoration: none;
       padding: 8px 15px; border-radius: 5px; font-weight: 600; font-size: 14px; white-space: nowrap; }
 .go:hover { filter: brightness(1.08); }
 .tick { margin-left: 12px; transform: scale(1.25); cursor: pointer; }
 .noemail li { margin-bottom: 5px; }
 code { background: rgba(128,128,128,.13); padding: 1px 5px; border-radius: 3px; font-size: 13px; }
</style>
<h1>Provider outreach</h1>
<p class="lede">One click opens a Gmail compose window with the mail already written.
Click the QR to copy it, then paste it into the message before sending — a compose
link cannot carry an attachment. The tick is only for your own bookkeeping; it is
remembered in this browser.</p>
"""


def write_index(rows, no_email, out, account=None):
    import base64
    from html import escape as e

    parts = [INDEX_HEAD]
    by_country = {}
    for r in rows:
        by_country.setdefault(r["country"], []).append(r)

    for country in sorted(by_country):
        # Sort accent-blind, so École lands under E rather than after Y.
        def key(r):
            folded = unicodedata.normalize("NFKD", r["title"].casefold())
            return "".join(c for c in folded if not unicodedata.combining(c))

        group = sorted(by_country[country], key=key)
        parts.append(f"<h2>{e(country)} — {len(group)} mails</h2>")
        for r in group:
            png = r["qr_path"]
            img = ""
            if png and png.is_file():
                data = base64.b64encode(png.read_bytes()).decode()
                img = (f'<img src="data:image/png;base64,{data}" title="click to copy" '
                       f'alt="QR code for {e(r["title"])}">')
            lang = f'<span class="lang">{r["lang"] or "en"}</span>'
            parts.append(
                f'<div class="row" data-code="{e(r["code"])}">{img}'
                f'<div><div class="name">{e(r["title"])}{lang}</div>'
                f'<div class="meta">{e(r["email"])} · {e(r["location_name"])} · '
                f'<code>{e(r["code"])}</code></div></div>'
                f'<div><a class="go" target="_blank" rel="noopener" '
                f'href="{e(gmail_url(r, account))}">Compose</a>'
                f'<input class="tick" type="checkbox"></div></div>'
            )

    if no_email:
        parts.append(f"<h2>No email published — {len(no_email)}</h2><ul class=\"noemail\">")
        for r in no_email:
            site = r["url"] or "(no website either)"
            href = site if site.startswith("http") else f"https://{site}"
            parts.append(f'<li>{e(r["title"])} — <a href="{e(href)}" target="_blank" '
                         f'rel="noopener">{e(site)}</a> → <code>{e(r["link"])}</code></li>')
        parts.append("</ul>")

    parts.append("""
<script>
const KEY = 'world66-outreach-done';
let done = [];
try { done = JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) {}
document.querySelectorAll('.row').forEach(row => {
  const code = row.dataset.code, box = row.querySelector('.tick');
  if (!box) return;
  if (done.includes(code)) { box.checked = true; row.classList.add('done'); }
  box.addEventListener('change', () => {
    row.classList.toggle('done', box.checked);
    done = box.checked ? [...new Set([...done, code])] : done.filter(c => c !== code);
    try { localStorage.setItem(KEY, JSON.stringify(done)); } catch (e) {}
  });
  row.querySelector('.go')?.addEventListener('click', () => {
    box.checked = true; box.dispatchEvent(new Event('change'));
  });
});
document.querySelectorAll('.row img').forEach(img => {
  img.addEventListener('click', async () => {
    try {
      const blob = await (await fetch(img.src)).blob();
      await navigator.clipboard.write([new ClipboardItem({'image/png': blob})]);
      img.style.outline = '3px solid var(--accent)';
      setTimeout(() => { img.style.outline = ''; }, 700);
    } catch (e) { alert('Copy failed — right-click the QR and copy it instead.'); }
  });
});
</script>
""")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assign", action="store_true", help="assign codes where missing")
    ap.add_argument("--qr", action="store_true", help="write QR PNG and SVG files")
    ap.add_argument("--emails", action="store_true", help="write the outreach emails")
    ap.add_argument("--print", action="store_true", help="also print each draft to stdout")
    ap.add_argument("--index", action="store_true",
                    help="write an HTML page of one-click Gmail compose links")
    ap.add_argument("--gmail-account", type=int, default=None,
                    help="pin the compose links to Gmail account N (0 is the first)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--country", default="", help="limit to a content path fragment")
    args = ap.parse_args()

    if not (args.assign or args.qr or args.emails or args.index):
        ap.error("nothing to do — pass --assign, --qr, --emails and/or --index")
    if args.index:
        args.qr = True   # the page embeds the QR images

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
            "country": country_of(rel),
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

    for r in rows:
        text = compose(r)
        header, _, body = text.partition("\n\n")
        r["subject"] = next(l.split(":", 1)[1].strip() for l in header.split("\n")
                            if l.lower().startswith("subject:"))
        r["body"] = body.strip() + "\n"
        r["qr_path"] = Path(args.out) / f'{r["slug"]}-{r["code"]}.png'

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

    if args.index:
        index = Path(args.out) / "index.html"
        with_email = [r for r in rows if r["email"]]
        write_index(with_email, [r for r in rows if not r["email"]], index,
                    args.gmail_account)
        print(f"wrote {index} — {len(with_email)} compose links")

    print(f"\n{len(rows)} provider{'s' if len(rows) != 1 else ''} with codes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
