"""Send the blog drafts for a content path through Resend, skipping anyone Resend has already mailed.

    python3 tools/blog_outreach.py --city <path> --emails
    python3 .claude/skills/outreach/send_blogs.py <path>
    python3 tools/blog_outreach.py --city <path> --mark-sent
"""
import csv, glob, sys, time, urllib.error
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import resend

path = sys.argv[1]
FROM = "Richard at World66 <richard@world66.ai>"
sent = resend.mailed() | resend.gmail_mailed()
targets = [r for r in csv.DictReader(open("tools/blog_outreach.csv"))
           if path in r["list_path"] and r["contact_type"] == "email" and not r["emailed"]]
drafts = {}
for f in glob.glob("build/outreach/blogs/*.txt"):
    t = open(f).read()
    drafts[t.split("\n", 1)[0].replace("To:", "").strip().lower()] = t
ok = failed = 0
for r in targets:
    to = r["contact"].lower()
    if to in sent:
        print("SKIP already mailed", to); continue
    t = drafts.get(to)
    if not t:
        failed += 1; print("NO DRAFT", to); continue
    head, _, body = t.partition("\n\n")
    subject = [l.split(":", 1)[1].strip() for l in head.splitlines() if l.lower().startswith("subject:")][0]
    try:
        res = resend.post({"from": FROM, "to": [r["contact"]], "subject": subject,
                           "text": body.strip() + "\n", "reply_to": "richard@world66.ai"})
        ok += 1; sent.add(to); print("sent", r["blog_name"], res.get("id"))
    except urllib.error.HTTPError as e:
        failed += 1; print("FAIL", to, e.code, e.read()[:150])
    time.sleep(0.7)
print(ok, "sent")
if failed:
    sys.exit(f"{failed} not sent; do not mark the batch sent")
