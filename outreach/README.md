# Provider outreach

Who we have written to, and what came back. `log.csv` is the record — one row per
provider, keyed by the `outreach_code` in that provider's frontmatter.

The tick boxes on the generated index page live in one browser's `localStorage`.
They are a "where was I" marker, not a record. This file is the record, which is
why it is committed: it survives a cleared browser, a second machine and a
second person.

## The columns

| | |
|---|---|
| `code` | the provider's `outreach_code`; resolves at `world66.ai/qr/<CODE>` |
| `provider`, `country`, `location`, `email`, `lang` | derived from `content/`, refreshed on every sync |
| `channel` | `email`, or `website` where they publish no address and need a contact form by hand |
| `sent_at` | set once, never rewritten |
| `bounced`, `replied_at`, `outcome`, `notes` | filled in by hand; a sync never overwrites these |

## Working with it

```bash
python3 tools/provider_qr.py --ledger       # add rows for new providers, refresh derived columns
python3 tools/provider_qr.py --mark-sent    # stamp today on mailable rows with no date
python3 tools/provider_qr.py --emails --index
open build/outreach/index.html
```

Rows already carrying a `sent_at` show as sent on that page whatever browser it
opens in. The page's tick boxes remain a local progress marker. After sending a
whole batch, stamp it with `--mark-sent`; for a partial batch, fill in `sent_at`
for those rows by hand.

Limit a batch with `--country`:

```bash
python3 tools/provider_qr.py --country suriname --mark-sent
```

`--mark-sent` never re-stamps a row that already has a date, so running it twice
cannot rewrite history. `--ledger` never touches the hand-written columns.

## This repository is public

The provider email addresses are already public — they are in each provider's
frontmatter and rendered on the site. The dates are harmless.

`outcome` and `notes` are the ones to think about: they are statements about a
named third party, in public git history, permanently. Keep them factual and
short. **If a provider asks to be removed, delete their page — do not write up
the request here.**

## Bounces are content bugs

A hard bounce means the `email:` in that provider's markdown is wrong. Fix it at
the source or drop the field; do not just note it here.

# Blog outreach

The blogs featured on a `type: bloglist` page, and who has been told. The record
is [`tools/blog_outreach.csv`](../tools/blog_outreach.csv), not a file in here —
that CSV already existed, and the linter's `bloglist_contacts` check fails if a
featured blog has no row in it, so it is the contact list and the ledger at once.
`tools/activity_outreach.py` is why: a second, competing record of who had been
contacted had to be retired.

## The columns

| | |
|---|---|
| `city`, `list_path`, `blog_name`, `blog_url` | derived from `content/`, refreshed on every sync |
| `contact_type` | `email`, or `form` where the blog publishes no address |
| `contact` | the address, or the contact-page URL to fill in by hand |
| `emailed` | set once, never rewritten |
| `bounced`, `replied_at`, `outcome`, `notes` | filled in by hand; a sync never overwrites these |

## Working with it

```bash
python3 tools/blog_outreach.py --ledger          # add rows for newly featured blogs
python3 tools/blog_outreach.py --emails --index
open build/outreach/blogs/index.html
python3 tools/blog_outreach.py --mark-sent       # stamp today on mailable rows with no date
```

Limit a batch with `--city`:

```bash
python3 tools/blog_outreach.py --city sarajevo --emails --index
```

`--mark-sent` never re-stamps a row that already has a date. `--ledger` never
touches the hand-written columns.

## What the mail says

It leads with the link to the blog's own entry, highlighted, and the number of
our pages that already credit them. Then it asks for two things in order: **a
link back**, which is the ask, and **content** — a correction, a paragraph, a
photo they own — which we would rather have and say so.

It also says plainly that nobody paid to be on the list and nothing is expected
in return. That sentence is not padding: without it a "we featured you, now link
to us" mail reads like the opening of a deal, and [BLOGLISTS.md](../BLOGLISTS.md)
rule 5 says there isn't one.

## Roughly half have no email

33 of 65 publish only a contact form. Those are listed separately at the foot of
the index page with the link to paste, and have to be done by hand. Leave their
`emailed` blank until they actually are.
