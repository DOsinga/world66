"""Shared helpers: the Resend key from .env, GET/POST, the local mail archive, and every
address we have mailed.

Resend forgets mail after a few weeks: by November 2026 it held 12 of the 600-odd
messages sent since October. So every read first copies whatever is new into a
local archive, and the duplicate check and the inbox read from the archive.
"""
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


API = "https://api.resend.com/emails"


def archive_dir():
    """Outside the repository: these are other people's mails."""
    return Path(os.environ.get("OUTREACH_ARCHIVE") or Path.home() / "Repos/mails/resend")


def _pages(url):
    rows, after = [], None
    for _ in range(500):
        d = get(f"{url}?limit=100" + (f"&after={after}" if after else ""))
        page = d.get("data", [])
        rows += page
        if not d.get("has_more") or not page:
            break
        after = page[-1]["id"]
    return rows


def archive():
    """Copy every message Resend still holds and we have not stored yet. Returns how many."""
    new = 0
    for kind, url in (("sent", API), ("received", API + "/receiving")):
        folder = archive_dir() / kind
        folder.mkdir(parents=True, exist_ok=True)
        for row in _pages(url):
            target = folder / f"{row['id']}.json"
            if target.exists():
                continue
            message = get(f"{url}/{row['id']}")
            if kind == "received":
                saved = []
                try:
                    attachments = get(f"{url}/{row['id']}/attachments").get("data", [])
                except Exception:
                    attachments = []
                for x in attachments:
                    if x.get("download_url"):
                        dest = folder / row["id"] / os.path.basename(x.get("filename") or x["id"])
                        dest.parent.mkdir(exist_ok=True)
                        urllib.request.urlretrieve(x["download_url"], dest)
                        saved.append(str(dest))
                message["saved_attachments"] = saved
            tmp = target.with_suffix(".tmp")
            tmp.write_text(json.dumps(message, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(target)
            new += 1
    return new


def _archived(kind):
    rows = []
    for f in (archive_dir() / kind).glob("*.json"):
        try:
            rows.append(json.loads(f.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return sorted(rows, key=lambda m: m.get("created_at") or "", reverse=True)


def mailed():
    """Every address we have sent to through Resend, cc and bcc included."""
    archive()
    sent = set()
    for m in _archived("sent"):
        for field in ("to", "cc", "bcc"):
            value = m.get(field) or []
            sent.update(a.lower() for a in ([value] if isinstance(value, str) else value))
    return sent


def inbox():
    """Every message received, newest first, with its full text."""
    archive()
    return _archived("received")


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
