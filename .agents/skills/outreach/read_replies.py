"""Print the replies from the given addresses (newest first), quoted history cut, attachments saved.

    python3 .claude/skills/outreach/read_replies.py someone@example.com [--out DIR]
"""
import argparse, os, re, urllib.request
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import resend

ap = argparse.ArgumentParser()
ap.add_argument("addresses", nargs="+")
ap.add_argument("--out", default="build/outreach/replies")
a = ap.parse_args()
want = {x.lower() for x in a.addresses}
for m in resend.inbox():
    if (m.get("from") or "").lower() not in want:
        continue
    d = resend.get("https://api.resend.com/emails/receiving/" + m["id"])
    text = d.get("text") or re.sub("<[^>]+>", " ", d.get("html") or "")
    text = re.split(r"\n(?:On .{5,120}wrote:|El .{5,120}escribió:|-----Original|-----Mensaje|From: |De: )", text)[0]
    print("=====", m["from"], m["created_at"][:16], m.get("subject"))
    print("message_id:", d.get("message_id"), "| cc:", d.get("cc"))
    print(text.strip(), "\n")
    try:
        att = resend.get(f"https://api.resend.com/emails/receiving/{m['id']}/attachments").get("data", [])
    except Exception:
        att = []
    for x in att:
        if x.get("download_url"):
            os.makedirs(a.out, exist_ok=True)
            dest = os.path.join(a.out, os.path.basename(x["filename"]))
            urllib.request.urlretrieve(x["download_url"], dest)
            print("attachment saved:", dest)
