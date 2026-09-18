#!/usr/bin/env python3
"""Blog outreach: telling the blogs on our bloglists that they are featured.

The same shape as tools/provider_qr.py, for a different audience. A provider
gets a highlight code and a QR poster; a blog gets a link to the list it is on,
with its own entry highlighted, and a request for a link back.

There is deliberately no second ledger. tools/blog_outreach.csv already exists —
the linter's `bloglist_contacts` check fails if a featured blog has no row in
it — so that file is both the contact list and the record of who has been
written to. tools/activity_outreach.py is the cautionary tale: it wrote a
second, competing record of who had been contacted, and had to be retired.

What the mail asks for
----------------------
Two things, in this order:

1. **A link back.** This is the ask. An independent guide with no ad budget is
   found through other people's links or not at all, and a blogger who already
   writes about the city is exactly who a reader would trust the pointer from.

2. **Content, if they would rather give that.** A correction, a paragraph, a
   photo they own, a place we missed — published with their name and a link on
   it. We would rather have that than the link, and saying so is honest: we are
   trying to build the best travel guide there is and cannot do it alone.

Nobody paid to be on a list and nothing is asked in exchange for staying on it.
The mail says that too, because a "we featured you, now link to us" mail that
does not say it reads like the beginning of a deal. See BLOGLISTS.md rule 5.

Usage:
    python3 tools/blog_outreach.py --ledger              # add rows, refresh derived columns
    python3 tools/blog_outreach.py --emails --index      # write drafts + the compose page
    python3 tools/blog_outreach.py --mark-sent           # stamp today on unsent mailable rows
    python3 tools/blog_outreach.py --emails --index --city tbilisi

    --out DIR   drafts and the index page (default: build/outreach/blogs, gitignored)
    --base URL  site root for the links (default: https://world66.ai)
"""

from __future__ import annotations

import argparse
import csv
import datetime
import re
import sys
import textwrap
import unicodedata
import urllib.parse
from html import escape
from pathlib import Path

import frontmatter

REPO = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO / "content"
CONTACTS = REPO / "tools" / "blog_outreach.csv"
DEFAULT_OUT = REPO / "build" / "outreach" / "blogs"
DEFAULT_BASE = "https://world66.ai"

# The file predates this script and the linter joins on it, so the first seven
# columns are fixed. The rest mirror outreach/log.csv so a blog row records the
# same things a provider row does.
FIELDS = ["city", "list_path", "blog_name", "blog_url", "contact_type", "contact",
          "emailed", "bounced", "replied_at", "outcome", "notes"]

# Blogs write in their own language; the list is short enough to name them.
LANG_BY_DOMAIN = {
    "unaideaunviaje.com": "es",
}


def display_domain(url):
    host = url.split("//", 1)[-1].split("/", 1)[0]
    return host[4:] if host.startswith("www.") else host


def bloglists():
    """Every type: bloglist page, with its entries and the city it belongs to."""
    out = []
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        try:
            post = frontmatter.load(path)
        except Exception:
            continue
        if post.metadata.get("type") != "bloglist":
            continue
        rel = str(path.relative_to(CONTENT_DIR)).removesuffix(".md")
        city_md = path.parent.with_suffix(".md")
        city = rel.rsplit("/", 2)[-2].replace("_", " ").title()
        if city_md.is_file():
            try:
                city = str(frontmatter.load(city_md).metadata.get("title") or city)
            except Exception:
                pass
        out.append({"rel": rel, "city": city, "title": str(post.metadata.get("title") or ""),
                    "entries": list(post.metadata.get("blogs") or [])})
    return out


def credited_pois(list_rel, blog_url):
    """POIs in this list's own directory whose sources name this blog.

    The count is the concrete thing the mail can offer — "nine of our Sarajevo
    pages credit you" is a fact about the site, not a compliment.
    """
    d = CONTENT_DIR / list_rel.rsplit("/", 1)[0]
    n = 0
    for md in d.glob("*.md"):
        try:
            meta = frontmatter.load(md).metadata
        except Exception:
            continue
        if meta.get("type") != "poi":
            continue
        if blog_url in (meta.get("sources") or []):
            n += 1
    return n


def rows_from_content(base=DEFAULT_BASE, city_filter=""):
    """One row per featured blog, joined to its contact details."""
    contacts = {}
    if CONTACTS.is_file():
        with open(CONTACTS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                contacts[(r.get("list_path", ""), r.get("blog_url", ""))] = r

    rows = []
    for bl in bloglists():
        if city_filter and city_filter.lower() not in bl["rel"].lower():
            continue
        for e in bl["entries"]:
            url = str(e.get("url") or "").strip()
            if not url:
                continue
            domain = display_domain(url)
            held = contacts.get((bl["rel"], url), {})
            contact = (held.get("contact") or "").strip()
            ctype = (held.get("contact_type") or "").strip()
            rows.append({
                "city": bl["city"],
                "list_path": bl["rel"],
                "list_title": bl["title"],
                "blog_name": str(e.get("blog") or e.get("name") or domain),
                "blog_url": url,
                "domain": domain,
                "author": str(e.get("author") or "").strip(),
                # The reader lands on the list with their own entry marked — the
                # same highlight a POI's "Listed by" tag uses.
                "link": f'{base}/{bl["rel"]}?blog={domain}#blog-{domain.replace(".", "-")}',
                "contact_type": ctype,
                "contact": contact,
                "email": contact if ctype == "email" else "",
                "lang": LANG_BY_DOMAIN.get(domain, "en"),
                "credited": credited_pois(bl["rel"], url),
                "emailed": (held.get("emailed") or "").strip(),
            })
    return rows


HEADER = """To: {email}
Subject: {blog_name} is on our {city} reading list

"""

BODY = {
    "en": """Hello{salutation},

We run World66, an open travel guide that has been going in one form or another
since 2001. We have just put together a short reading list for {city} — the few
blogs we think are genuinely worth a traveller's time before they go — and
{blog_name} is on it:

{link}

Your entry is highlighted when you open that link.{credit_line}

Nobody paid to be on the list and there is nothing to sign up for. Two things
would help us, though, if you are willing:

1. A link back is worth more to us than anything else. A line at the foot of
   your {city} post, or a spot on a resources page, pointing at the list above.
   A guide like ours with no ad budget gets found through other people's links
   or it does not get found at all.

2. If you would rather share something than link to something, we would like
   that even more. A correction, a paragraph, a photo you own, a place we have
   missed — send it over and we will put it up with your name and a link on it.
   We are trying to build the best travel guide in the world and we are not
   going to manage that on our own.

Either way, thank you for writing the thing that got you on the list.
""",

    "es": """Hola{salutation},

Llevamos World66, una guía de viajes abierta que existe de una forma u otra
desde 2001. Acabamos de preparar una pequeña lista de lecturas sobre {city} —
los pocos blogs que de verdad merecen el tiempo de un viajero antes de ir — y
{blog_name} está en ella:

{link}

Al abrir ese enlace, su entrada aparece resaltada.{credit_line}

Nadie ha pagado por estar en la lista y no hay que registrarse en nada. Aun
así, hay dos cosas que nos ayudarían mucho:

1. Un enlace de vuelta vale más para nosotros que cualquier otra cosa. Una
   línea al final de su artículo sobre {city}, o un hueco en una página de
   recursos, que apunte a la lista de arriba. Una guía como la nuestra, sin
   presupuesto de publicidad, se encuentra a través de los enlaces de otros o
   no se encuentra.

2. Y si prefiere compartir algo en lugar de enlazar algo, nos gustaría todavía
   más. Una corrección, un párrafo, una foto suya, un sitio que se nos haya
   escapado — envíenoslo y lo publicamos con su nombre y un enlace. Queremos
   hacer la mejor guía de viajes del mundo y solos no vamos a conseguirlo.

En cualquier caso, gracias por escribir lo que le ha puesto en la lista.
""",
}

# One page or several — a mail that says "1 of our pages already credit you"
# announces that it was generated.
CREDIT = {
    "en": " {n} of our {city} pages already credit you as the source, each one linking"
          " back to the list.",
    "es": " {n} de nuestras páginas de {city} ya le citan como fuente, y cada una enlaza"
          " con la lista.",
}
CREDIT_ONE = {
    "en": " One of our {city} pages already credits you as the source, linking back"
          " to the list.",
    "es": " Una de nuestras páginas de {city} ya le cita como fuente, con un enlace"
          " a la lista.",
}

SIGNOFF = {
    "en": "Thanks,\nRichard & the World66 team",
    "es": "Un saludo,\nRichard y el equipo de World66",
}


def wrap(text, width=78):
    """Re-flow paragraphs after substitution, leaving bare URLs alone and keeping
    the hanging indent on numbered items."""
    out = []
    for block in text.split("\n\n"):
        lines = block.split("\n")
        if len(lines) == 1 and lines[0].startswith("http"):
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


def salutation(author):
    """" Amy and Angel", " Manjula", " Emily" — or "" where we hold no name.

    Naive first-token logic greets a four-initial Sri Lankan name as "Hello
    H.A.K.L." and a two-person blog as "Hello Amy", so both are special-cased.
    Two initials are left alone: C.K. Lam publishes as C.K.
    """
    author = (author or "").strip()
    if not author:
        return ""
    if re.search(r"\s*(?:&| and )\s*", author):
        names = [p.split()[0] for p in re.split(r"\s*(?:&| and )\s*", author) if p.split()]
        return " " + " and ".join(names)
    tokens = author.split()
    if re.fullmatch(r"(?:[A-Z]\.){3,}", tokens[0]) and len(tokens) > 1:
        return " " + tokens[-1]
    return " " + tokens[0]


def compose(row):
    lang = row["lang"] if row["lang"] in BODY else "en"
    credit_line = ""
    if row["credited"] == 1:
        credit_line = CREDIT_ONE[lang].format(city=row["city"])
    elif row["credited"]:
        credit_line = CREDIT[lang].format(n=row["credited"], city=row["city"])
    fields = {
        "email": row["email"], "blog_name": row["blog_name"], "city": row["city"],
        "link": row["link"], "credit_line": credit_line,
        # Only greet by name where we actually hold one.
        "salutation": salutation(row["author"]),
    }
    body = f'{wrap(BODY[lang].format(**fields))}\n\n{SIGNOFF[lang]}\n'
    return HEADER.format(**fields) + body


def subject(row):
    return f'{row["blog_name"]} is on our {row["city"]} reading list'


def gmail_url(row, account=None):
    """A prefilled Gmail compose window — no credentials, no API. Opens in
    whatever account the browser is already signed in to."""
    prefix = (f"https://mail.google.com/mail/u/{account}/" if account is not None
              else "https://mail.google.com/mail/")
    query = urllib.parse.urlencode({
        "view": "cm", "fs": "1", "tf": "1",
        "to": row["email"], "su": subject(row), "body": row["body"],
    }, quote_via=urllib.parse.quote)
    return f"{prefix}?{query}"


INDEX_HEAD = """<!doctype html>
<meta charset="utf-8">
<title>World66 blog outreach</title>
<style>
 :root { color-scheme: light dark; --line: #d9d4cc; --ink: #24211d; --dim: #6d675f;
         --paper: #fbf9f5; --accent: #1a6b52; }
 @media (prefers-color-scheme: dark) {
   :root { --line: #38342e; --ink: #ece7df; --dim: #97907f; --paper: #171512;
           --accent: #58c79e; } }
 body { background: var(--paper); color: var(--ink); margin: 0 auto; padding: 32px 20px 80px;
        max-width: 940px; font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
 h1 { font-size: 22px; margin: 0 0 4px; }
 .lede { color: var(--dim); margin: 0 0 28px; max-width: 64ch; }
 h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .09em; color: var(--dim);
      margin: 32px 0 10px; border-bottom: 1px solid var(--line); padding-bottom: 6px; }
 .row { display: grid; grid-template-columns: 1fr auto; gap: 16px; align-items: center;
        padding: 12px 10px; border-bottom: 1px solid var(--line); border-radius: 6px; }
 .row.done { opacity: .42; }
 .name { font-weight: 600; }
 .meta { color: var(--dim); font-size: 13px; }
 .lang { display: inline-block; font-size: 11px; letter-spacing: .06em; text-transform: uppercase;
         border: 1px solid var(--line); border-radius: 3px; padding: 1px 5px; margin-left: 7px;
         color: var(--dim); }
 .go { display: inline-block; background: var(--accent); color: #fff; text-decoration: none;
       padding: 8px 15px; border-radius: 5px; font-weight: 600; font-size: 14px; white-space: nowrap; }
 .go:hover { filter: brightness(1.08); }
 .tick { margin-left: 12px; transform: scale(1.25); cursor: pointer; }
 .forms li { margin-bottom: 6px; }
 code { background: rgba(128,128,128,.13); padding: 1px 5px; border-radius: 3px; font-size: 13px; }
 .sent { color: var(--accent); font-weight: 600; }
 a { color: var(--accent); }
</style>
<h1>Blog outreach</h1>
<p class="lede">One click opens a Gmail compose window with the mail already written.
Each mail links the blog's own entry on its list, highlighted, and asks for a link
back — or for content, which we would rather have.</p>
<p class="lede">Rows with a date in <code>tools/blog_outreach.csv</code> show as sent.
Tick boxes only track progress in this browser; record finished batches in the CSV
with <code>--mark-sent</code>.</p>
"""


def write_index(rows, forms, out, account=None):
    parts = [INDEX_HEAD]
    by_city = {}
    for r in rows:
        by_city.setdefault(r["city"], []).append(r)

    for city in sorted(by_city):
        def key(r):
            folded = unicodedata.normalize("NFKD", r["blog_name"].casefold())
            return "".join(c for c in folded if not unicodedata.combining(c))

        group = sorted(by_city[city], key=key)
        n = len(group)
        parts.append(f'<h2>{escape(city)} — {n} mail{"" if n == 1 else "s"}</h2>')
        for r in group:
            lang = f'<span class="lang">{r["lang"]}</span>'
            was_sent = bool(r["emailed"])
            stamp = f' · <span class="sent">sent {escape(r["emailed"])}</span>' if was_sent else ""
            credit = f' · {r["credited"]} POIs credited' if r["credited"] else ""
            parts.append(
                f'<div class="row{" done" if was_sent else ""}" '
                f'data-code="{escape(r["list_path"] + "|" + r["blog_url"])}">'
                f'<div><div class="name">{escape(r["blog_name"])}{lang}</div>'
                f'<div class="meta">{escape(r["email"])} · '
                f'<a href="{escape(r["link"])}" target="_blank" rel="noopener">'
                f'{escape(r["domain"])}</a>{escape(credit)}{stamp}</div></div>'
                f'<div><a class="go" target="_blank" rel="noopener" '
                f'href="{escape(gmail_url(r, account))}">Compose</a>'
                f'<input class="tick" type="checkbox"{" checked" if was_sent else ""}>'
                f'</div></div>'
            )

    if forms:
        parts.append(f'<h2>Contact form — {len(forms)} by hand</h2><ul class="forms">')
        for r in forms:
            where = r["contact"] or r["blog_url"]
            parts.append(
                f'<li><strong>{escape(r["blog_name"])}</strong> ({escape(r["city"])}) — '
                f'<a href="{escape(where)}" target="_blank" rel="noopener">{escape(where)}</a>'
                f' → paste the link <code>{escape(r["link"])}</code></li>')
        parts.append("</ul>")

    parts.append("""
<script>
const KEY = 'world66-blog-outreach-done';
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
</script>
""")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def load_contacts():
    if not CONTACTS.is_file():
        return []
    with open(CONTACTS, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_contacts(rows):
    with open(CONTACTS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r.get("city", ""), r.get("blog_name", "").casefold())):
            w.writerow({k: r.get(k, "") for k in FIELDS})


def sync(rows):
    """Add a row per featured blog and refresh the derived columns.

    Never touches emailed/bounced/replied_at/outcome/notes — those are the
    record. A blog dropped from a list keeps its row: we still wrote to them.
    """
    held = load_contacts()
    by_key = {(r.get("list_path", ""), r.get("blog_url", "")): r for r in held}
    added = 0
    for r in rows:
        key = (r["list_path"], r["blog_url"])
        row = by_key.get(key)
        if row is None:
            row = {k: "" for k in FIELDS}
            added += 1
        row.update({"city": r["city"], "list_path": r["list_path"],
                    "blog_name": r["blog_name"], "blog_url": r["blog_url"]})
        # Only fill contact details we do not already hold; they are researched
        # by hand off each blog's own contact page.
        row.setdefault("contact_type", "")
        by_key[key] = row
    save_contacts(list(by_key.values()))
    return added, len(by_key)


def mark_sent(when, city_filter=""):
    """Stamp `emailed` on mailable rows with no date. Never re-stamps."""
    held = load_contacts()
    n = 0
    for r in held:
        if r.get("contact_type") != "email" or r.get("emailed"):
            continue
        if city_filter and city_filter.lower() not in r.get("list_path", "").lower():
            continue
        r["emailed"] = when
        n += 1
    save_contacts(held)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", action="store_true",
                    help="add rows for newly featured blogs, refresh derived columns")
    ap.add_argument("--emails", action="store_true", help="write the outreach drafts")
    ap.add_argument("--index", action="store_true",
                    help="write an HTML page of one-click Gmail compose links")
    ap.add_argument("--print", action="store_true", help="also print each draft to stdout")
    ap.add_argument("--mark-sent", action="store_true",
                    help="stamp today on mailable rows with no date")
    ap.add_argument("--gmail-account", type=int, default=None,
                    help="pin the compose links to Gmail account N (0 is the first)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="drafts and index (gitignored)")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--city", default="", help="limit to a content path fragment")
    args = ap.parse_args()

    rows = rows_from_content(args.base, args.city)
    if not rows:
        sys.exit("No bloglists found under content/.")

    if args.ledger:
        added, total = sync(rows_from_content(args.base))
        print(f"{CONTACTS.relative_to(REPO)}: {total} rows ({added} new)")

    # Re-read so the drafts see whatever --ledger just wrote.
    rows = rows_from_content(args.base, args.city)
    mailable = [r for r in rows if r["email"]]
    forms = [r for r in rows if not r["email"]]

    if args.mark_sent:
        when = datetime.date.today().isoformat()
        print(f"marked {mark_sent(when, args.city)} rows sent {when}")
        rows = rows_from_content(args.base, args.city)
        mailable = [r for r in rows if r["email"]]
        forms = [r for r in rows if not r["email"]]

    if args.emails or args.index:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for r in mailable:
            r["body"] = compose(r).split("\n\n", 1)[1]
            if args.emails:
                slug = re.sub(r"[^a-z0-9]+", "_", r["blog_name"].casefold()).strip("_")
                city = r["list_path"].rsplit("/", 2)[-2]
                (out / f"{city}_{slug}.txt").write_text(compose(r), encoding="utf-8")
            if args.print:
                print(compose(r))
                print("-" * 78)
        if args.emails:
            print(f"{len(mailable)} drafts -> {out}")
        if args.index:
            write_index(mailable, forms, out / "index.html", args.gmail_account)
            print(f"index -> {out / 'index.html'}")

    sent = sum(1 for r in rows if r["emailed"])
    print(f"{len(rows)} featured blogs · {len(mailable)} mailable · "
          f"{len(forms)} contact form · {sent} already written to")


if __name__ == "__main__":
    main()
