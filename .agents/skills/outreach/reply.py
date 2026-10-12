"""Answer the latest message from an address, threaded on it, through Resend.

    python3 .claude/skills/outreach/reply.py someone@example.com body.txt [--cc other@example.com]

Only after the user has seen the text and said to send it.
"""
import argparse, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import resend

ap = argparse.ArgumentParser()
ap.add_argument("to")
ap.add_argument("body")
ap.add_argument("--cc", action="append", default=[])
a = ap.parse_args()
msgs = [m for m in resend.inbox() if (m.get("from") or "").lower() == a.to.lower()]
if not msgs:
    sys.exit(f"nothing received from {a.to}")
m = msgs[0]
mid = resend.get("https://api.resend.com/emails/receiving/" + m["id"]).get("message_id")
subject = m["subject"] if m["subject"].lower().startswith("re:") else "Re: " + m["subject"]
payload = {"from": "Richard at World66 <richard@world66.ai>", "to": [a.to], "subject": subject,
           "text": open(a.body).read(), "headers": {"In-Reply-To": mid, "References": mid}}
if a.cc:
    payload["cc"] = a.cc
print(resend.post(payload))
