#!/usr/bin/env python3
"""Find the WhatsApp number a business actually advertises.

Used by the activity-providers skill. We only publish a WhatsApp number a
provider genuinely advertises — nearly every mobile is on WhatsApp, but that is
not consent to receive strangers' bookings there.

Renders each page in headless Chrome, so JavaScript-injected links and chat
widgets resolve, and looks for four things in descending order of confidence:

  1. wa.me / api.whatsapp.com / web.whatsapp.com links       — explicit
  2. chat-widget config ("Click to Chat", Chatway, and kin)  — explicit
  3. the word WhatsApp beside a phone number in visible text — advertised
  4. the word WhatsApp with no number near it                — mention only

(3) matters outside Europe: in Suriname, Guyana and much of Latin America the
number is written in prose ("Bereikbaar op WhatsApp ... +597 885 8495") rather
than linked, and a link-only check finds nothing at all.

Results are a starting point, not an answer. Known failure modes, all observed:
  - a wa.me link belonging to the web agency credited in the site footer
  - TEXT matching a landline that merely sits near the word WhatsApp
  - none, because Cloudflare served the crawler an interstitial
  - none, because the number lives on /contact rather than the homepage
Check anything you intend to publish by reading the page.

Usage:
    python3 tools/wa_detect.py --cc 597 https://site1 https://site2 ...

--cc is the country calling code, digits only (33 France, 597 Suriname,
592 Guyana, 51 Peru). Roughly 1-3 minutes per site.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PATHS = ["", "/contact/", "/contact", "/contact-us/", "/nous-contacter/", "/over-ons/"]

LINK_RE = re.compile(
    r"(?:wa\.me/|(?:api|web)\.whatsapp\.com/send/?\?phone=)(\d{8,15})", re.I)
WIDGET_RE = re.compile(r'"channel"\s*:\s*"Whatsapp"\s*,\s*"value"\s*:\s*"(\d{8,15})"', re.I)
# "Click to Chat" (ht_ctc) is the commonest WhatsApp button on WordPress and
# keeps its number in plugin config, not in an href — Black Eagle Tours showed
# a WhatsApp button and two different phone numbers on the page, so guessing
# between them would have been a coin flip.
CTC_RE = re.compile(r'ht_ctc.{0,900}?"number"\s*:\s*"(\d{8,15})"', re.I | re.S)


def phone_re(cc):
    # +597 8123456 / 00597-812-3456 / (597) 8123456, and bare local 7-8 digit mobiles
    # Also "(597)-8782968" and "(+597)8568332": without the bracket form the
    # country code is dropped and the number comes out 7 digits short.
    return re.compile(
        r"\(?\+?%s\)?[\s\-\.]*\d[\d\s\-\.]{5,12}\d"
        r"|(?:\+|00)\s?%s[\s\-\.\)/]*\d[\d\s\-\.]{5,12}\d"
        r"|\b[78]\d{2}[\s\-\.]?\d{4}\b" % (cc, cc))


def render(url, budget=9000):
    """Render one page. Chrome is invoked exactly as it is from the shell:
    adding --user-data-dir made it abort (SIGABRT) and return nothing, which
    the caller would have read as "this business has no WhatsApp"."""
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu",
             f"--virtual-time-budget={budget}", "--dump-dom", url],
            capture_output=True, text=True, errors="replace", timeout=90)
        return r.stdout or ""
    except Exception:
        return ""


def clean(num):
    d = re.sub(r"\D", "", num)
    return d


def visible_text(dom):
    """Markup-free text. Searching raw HTML for 'whatsapp' near a number matches
    CSS class names (.wp-social-link-whatsapp) and adjacent social-icon labels,
    which produced a confident, wrong number on the first run."""
    dom = re.sub(r"<(script|style)\b.*?</\1>", " ", dom, flags=re.S | re.I)
    dom = re.sub(r"<[^>]+>", " ", dom)
    dom = dom.replace("&nbsp;", " ").replace("&#8203;", "")
    return re.sub(r"\s+", " ", dom)


def scan(host_url, cc):
    seen_mentions = []
    loaded_any = False
    prx = phone_re(cc)
    for path in PATHS:
        url = host_url.rstrip("/") + path
        dom = render(url)
        if len(dom) < 1500 and path == "":
            dom = render(url, budget=15000)   # retry the homepage only
        if len(dom) < 1500:
            continue
        loaded_any = True

        for m in LINK_RE.findall(dom) + WIDGET_RE.findall(dom) + CTC_RE.findall(dom):
            return ("link", "+" + m, url)

        text = visible_text(dom)
        for m in re.finditer(r"whatsapp", text, re.I):
            # Tight window, visible text only: "WhatsApp: +597 812-3456".
            window = text[m.end(): m.end() + 60]
            nums = [n for n in prx.findall(window) if 7 <= len(clean(n)) <= 15]
            if not nums:
                back = text[max(0, m.start() - 45): m.start()]
                nums = [n for n in prx.findall(back) if 7 <= len(clean(n)) <= 15]
            if nums:
                return ("text", "+" + clean(nums[0]), url)
            seen_mentions.append(url)

    if seen_mentions:
        return ("mention", "", seen_mentions[0])
    if not loaded_any:
        return ("error", "", "no page loaded")
    return ("none", "", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cc", default="597", help="country calling code, digits only")
    ap.add_argument("urls", nargs="+")
    args = ap.parse_args()
    for u in args.urls:
        kind, num, where = scan(u, args.cc)
        host = re.sub(r"^https?://", "", u).split("/")[0]
        label = {"link": "LINK", "text": "TEXT", "mention": "mention-only",
                 "none": "none", "error": "UNREACHABLE"}[kind]
        print(f"{host:42} {label:13} {num:18} {where}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
