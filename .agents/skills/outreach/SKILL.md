---
name: outreach
description: mail activity providers and featured blogs about their World66 listing through Resend, read the replies, and answer them. invoke when the user asks to reach out to, mail, or follow up with providers or blogs for a country or region, or asks whether anyone replied
argument-hint: <content path, e.g. europe/unitedkingdom/scotland> | replies
---

Outreach tells a provider or a blog that it is in the guide and gives it a link back. It goes out from Richard's laptop through Resend. Nothing has to be merged to *send*, but what a mail points at has to be live on world66.ai.

**Every address gets one mail.** The ledgers (`outreach/log.csv` for providers, `tools/blog_outreach.csv` for blogs) have under-recorded sends before: hundreds of Gmail sends were never stamped, and two providers were mailed twice. So the Resend log and the export of hand-sent Gmail mail (`~/Repos/mails/*.zip`, or `OUTREACH_GMAIL_EXPORT`), not the ledger, are the final check. Skipping the export once caused seven double mails.

## 1. Is it ready?

- The content is **merged and live**. Open one provider page and one bloglist on world66.ai.
- Every provider has an `outreach_code`. Codes are assigned in the provider PR itself (`tools/provider_qr.py --assign --qr --ledger`).
- Every featured blog has a row in `tools/blog_outreach.csv` with a contact.

## 2. A clean checkout of main

The main checkout is usually on someone's branch with localhost running. Don't switch it. Use a sparse, detached worktree instead:

```bash
git fetch -q origin
git worktree add --no-checkout --detach ../w66-send origin/main
cd ../w66-send
git sparse-checkout set --no-cone '/.agents/' '/.claude/' '/tools/' '/outreach/' '/guide/' '/world66/' '/manage.py' '/static/qr/' '/content/<path>/' '/content/<path>.md'
git checkout -q --detach origin/main
```

Until PR #2306 is merged, the Resend version of the tool lives only on its branch. Copy it in without committing:

```bash
git show origin/outreach-resend:tools/provider_qr.py > tools/provider_qr.py
```

## 3. Check the queue

```bash
source ../world66/venv/bin/activate
set -a; . ../world66/.env; set +a           # RESEND_API_KEY
python3 tools/provider_qr.py --country <path> --list    # who would be mailed
python3 tools/provider_qr.py --country <path> --audit   # ledger vs Resend
python3 .claude/skills/outreach/check_queue.py <path>   # every target vs the Resend log, both ledgers and the Gmail export
```

`check_queue.py` must report **no duplicates** before anything is sent. If it finds any, take those addresses out and say so.

`--audit` also lists replies you sent (they are Resend messages too). Don't run `--audit --fix` on those.

## 4. Ask

Report the counts to the user and **wait for an explicit go**:

- providers with an email, and providers with none
- blog emails, and blogs that only have a contact form (those are done by hand)
- the result of the duplicate check

A request like "can we reach out to X" is not a go.

## 5. Send

```bash
export OUTREACH_FROM="Richard at World66 <richard@world66.ai>"
python3 tools/provider_qr.py --country <path> --send       # writes sent_at to outreach/log.csv

python3 tools/blog_outreach.py --city <path> --emails      # drafts in build/outreach/blogs/
python3 .claude/skills/outreach/send_blogs.py <path>       # re-checks the Resend log, then sends
python3 tools/blog_outreach.py --city <path> --mark-sent
```

Only run `--mark-sent` when `send_blogs.py` exits successfully. A missing draft or failed send makes it exit nonzero so unsent rows are not stamped.

Test the path first with `--to <your address>` if anything about the mail has changed. `--to` marks nothing as sent.

Then commit the two ledgers on a branch off `origin/main` and open a PR ("Outreach: record the <place> send"). Remove the worktree afterwards.

List the contact-form blogs for the user, since these have to be done by hand.

## 6. Replies

```bash
python3 tools/provider_qr.py --replies                     # what came in, newest first
python3 .claude/skills/outreach/read_replies.py <address>... # full text, quotes cut, attachments saved
```

Summarise each reply for the user: what they ask, and what we would change. Then:

1. Make the fixes in a content PR.
2. **Wait until it is merged and live.** Check the page on world66.ai. A pushed PR is not live, and a reply that says "we fixed it" while the old page still shows breaks trust.
3. Draft the replies, show them, and **ask before sending**.
4. Send each reply threaded on the message it answers:

   ```bash
   python3 .claude/skills/outreach/reply.py <their address> <file with the body> [--cc addr]
   ```

5. Record outcomes: blogs in `tools/blog_outreach.csv` (`replied_at`, `outcome`, `notes`); providers with `--replies --stamp-replies` once #2306 is merged.

Write back in the language they wrote in. Answer every point they raised; don't commit to anything the user hasn't agreed to.

## Don't

- Don't send from Gmail. Resend is the only place the duplicate check can see.
- Don't send without a go, and don't take a go for one batch as a go for the next.
- Don't add a WhatsApp number from a reply unless they say it is for WhatsApp.
- Don't mail a provider twice. If it happened, say so in the next reply and apologise.
