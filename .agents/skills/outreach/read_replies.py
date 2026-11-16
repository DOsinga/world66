"""Print the replies from the given addresses (newest first), quoted history cut, and where their
attachments are kept in the archive. --out is accepted for old commands and ignored.

    python3 .claude/skills/outreach/read_replies.py someone@example.com [--out DIR]
"""
import argparse, os, re, urllib.request
from email.utils import parseaddr
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import resend

ap = argparse.ArgumentParser()
ap.add_argument("addresses", nargs="+")
ap.add_argument("--out", default="build/outreach/replies")
a = ap.parse_args()
want = {x.lower() for x in a.addresses}
for m in resend.inbox():
    if parseaddr(m.get("from") or "")[1].lower() not in want:
        continue
    d = m
    text = d.get("text") or re.sub("<[^>]+>", " ", d.get("html") or "")
    text = re.split(r"\n(?:On .{5,120}wrote:|El .{5,120}escribió:|-----Original|-----Mensaje|From: |De: )", text)[0]
    print("=====", m["from"], m["created_at"][:16], m.get("subject"))
    print("message_id:", d.get("message_id"), "| cc:", d.get("cc"))
    print(text.strip(), "\n")
    for path in m.get("saved_attachments") or []:
        print("attachment:", path)
