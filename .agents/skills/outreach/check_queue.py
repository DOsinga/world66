"""Check everyone outreach would mail for a content path against the Resend log, both ledgers
and the export of mail sent by hand from Gmail.

    python3 .claude/skills/outreach/check_queue.py europe/unitedkingdom/scotland

Run from the repo root of a main checkout, with the Resend version of provider_qr.py in tools/.
"""
import csv, re, subprocess, sys
from collections import Counter
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import resend

path = sys.argv[1]
out = subprocess.run([sys.executable, "tools/provider_qr.py", "--country", path, "--list"],
                     capture_output=True, text=True, check=True).stdout
providers = [l.split()[-1].lower() for l in out.splitlines() if re.match(r"  [A-Z0-9]{6} ", l)]
blogs = [r["contact"].lower() for r in csv.DictReader(open("tools/blog_outreach.csv"))
         if path in r["list_path"] and r["contact_type"] == "email" and not r["emailed"]]
forms = [r for r in csv.DictReader(open("tools/blog_outreach.csv"))
         if path in r["list_path"] and r["contact_type"] == "form" and not r["emailed"]]

ledgers = {r["email"].lower() for r in csv.DictReader(open("outreach/log.csv")) if r["sent_at"]}
ledgers |= {r["contact"].lower() for r in csv.DictReader(open("tools/blog_outreach.csv")) if r["emailed"]}
sent = resend.mailed()
gmail = resend.gmail_mailed()
targets = providers + blogs

print(f"{len(providers)} provider emails, {len(blogs)} blog emails, {len(forms)} blog contact forms (by hand)")
print(f"{len(sent)} addresses in the Resend log, {len(gmail)} in the Gmail export")
dup_resend = sorted(t for t in set(targets) if t in sent)
dup_ledger = sorted(t for t in set(targets) if t in ledgers)
dup_gmail = sorted(t for t in set(targets) if t in gmail)
repeated = sorted(t for t, n in Counter(targets).items() if n > 1)
print("already mailed via Resend:", dup_resend or "none")
print("already in a ledger:", dup_ledger or "none")
print("already mailed from Gmail:", dup_gmail or "none")
print("twice in this queue:", repeated or "none")
sys.exit(1 if dup_resend or dup_ledger or dup_gmail or repeated else 0)
