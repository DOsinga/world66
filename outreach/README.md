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
opens in. For rows you tick there, **Copy log rows** puts
`code,provider,email,sent_at` on the clipboard to paste in here.

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
