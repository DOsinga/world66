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
    return get("https://api.resend.com/emails/receiving").get("data", [])
