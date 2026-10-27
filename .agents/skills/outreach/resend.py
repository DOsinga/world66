"""Shared helpers: the Resend key from .env, GET/POST, and every address Resend has mailed."""
import json, os, re, urllib.request
from pathlib import Path


def key():
    if os.environ.get("RESEND_API_KEY"):
        return os.environ["RESEND_API_KEY"].strip()
    for d in [Path.cwd(), *Path.cwd().parents, Path.home() / "Repos/world66"]:
        env = d / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                m = re.match(r"\s*(?:export\s+)?RESEND_API_KEY\s*=\s*['\"]?([^'\"\n]+)", line)
                if m:
                    return m.group(1).strip()
    raise SystemExit("RESEND_API_KEY not found in the environment or a .env")


def _headers():
    return {"Authorization": "Bearer " + key(), "Content-Type": "application/json",
            "User-Agent": "world66-outreach/1.0 (+https://world66.ai)"}


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=_headers()), timeout=30))


def post(payload):
    req = urllib.request.Request("https://api.resend.com/emails", data=json.dumps(payload).encode(),
                                 headers=_headers(), method="POST")
    return json.load(urllib.request.urlopen(req, timeout=30))


def mailed():
    """Every address any Resend message has gone to, cc included."""
    sent, after = set(), None
    for _ in range(200):
        d = get("https://api.resend.com/emails?limit=100" + (f"&after={after}" if after else ""))
        rows = d.get("data", [])
        for r in rows:
            for field in ("to", "cc", "bcc"):
                sent.update(a.lower() for a in r.get(field) or [])
        if not d.get("has_more") or not rows:
            break
        after = rows[-1]["id"]
    return sent


def inbox():
    """Every message received, newest first. The API returns 20 a page unless told otherwise."""
    rows, after = [], None
    for _ in range(200):
        d = get("https://api.resend.com/emails/receiving?limit=100" + (f"&after={after}" if after else ""))
        page = d.get("data", [])
        rows += page
        if not d.get("has_more") or not page:
            break
        after = page[-1]["id"]
    return rows


def gmail_mailed(export_dir=None):
    """Every address mailed by hand from Gmail, read from the exported conversations.

    The export (zips of .eml files) holds whole threads: our own mails, whose
    recipients count as mailed, and the replies, whose senders were mailed first.
    Set OUTREACH_GMAIL_EXPORT to its folder; defaults to ~/Repos/mails.
    """
    import email, zipfile
    from email import policy
    from email.utils import getaddresses
    export_dir = Path(export_dir or os.environ.get("OUTREACH_GMAIL_EXPORT") or Path.home() / "Repos/mails")
    archives = sorted(export_dir.glob("*.zip"))
    if not archives:
        raise SystemExit(f"No Gmail export found in {export_dir}")
    me = {"richardosinga@gmail.com", "richard@world66.ai"}
    mailed = set()
    for archive in archives:
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                m = email.message_from_bytes(zf.read(info), policy=policy.default)
                frm = [a.lower() for _, a in getaddresses([str(m.get("From", ""))]) if a]
                rcpt = [a.lower() for _, a in getaddresses([str(m.get(h, "")) for h in ("To", "Cc", "Bcc")]) if a]
                if any(f in me for f in frm):
                    mailed.update(r for r in rcpt if r not in me)
                else:
                    mailed.update(f for f in frm if f not in me)
    return mailed
