# Picks

A pick is one person who lives near a place pointing at one thing worth noticing there. It is
stored on the POI it recommends, as a `picks:` entry, and it shows up twice: as a "Worth noticing"
box on the POI itself, and gathered into a "Picked by locals" callout on the location page.

## Why this exists

World66's rasa — the emotional flavour a page should leave you with — is *adbhuta*, the
marvellous: wonder, curiosity, and the delight of finding something you did not expect. Ours is
**practical wonder**. The world is enormous, strange and accessible, and every place contains
something worth noticing. Not glossy wanderlust or bucket-list anxiety; more a well-travelled
friend pointing at the map and saying *look, you can ski in Morocco — and here is how to get
there*.

Its second note is *vīra*, adventurous courage: the confidence to leave the standard route and go
where nobody else bothered to look. A trace of dry humour keeps it human. In two words: **curious
adventure**. As a product principle: *every page should reward curiosity and make exploration feel
possible.*

A guidebook writer passes through. The person who runs the kayak school, the bodega or the
penguin boat is there every day, and knows which bench catches the last light. A pick is how their
knowledge gets onto the page.

## The bar for a pick

- **Specific.** A named place and a reason: *sit outside by the sluices at the Koppelpoort*, not
  *the old town is lovely*.
- **Not the headline.** If it is already the first thing every visitor does, it is not a pick.
  The Perito Moreno glacier is not a pick; the hour when the tour buses have left is.
- **Something you can go and do.** A pick should make exploration feel possible — where it is, and
  ideally when.
- **In their words.** Edit for length and spelling, never for voice. If a provider writes it, it
  stays theirs.
- **One per person per place.** People who are asked for one thing choose better than people asked
  for ten.

## Frontmatter

On the POI being recommended:

```yaml
picks:
  - by: Example Kayak School          # illustrative — not a real provider
    provider: europe/somewhere/sometown/example_kayak_school
    quote: Paddle out past the second headland at low tide, where the seals haul out.
```

- **`by`** — the name to show. For a provider, their business name.
- **`quote`** — the pick itself, one or two sentences.
- **`provider`** — optional. The content path of the recommender's provider page. When it
  resolves, the pick links back to their listing, which is the reason a local business would take
  the time to write one. The linter's `pick_entries` check fails if it does not resolve.

The POI must already exist, or be created alongside the pick, in the location's own directory.
The location page collects picks from its own POIs only.

## How picks come in

The providers already have a WhatsApp number on the page and an outreach code in their
frontmatter, so the ask is a follow-up to a conversation we have already started:

> **One thing near you most visitors miss?**
>
> You are listed on World66 for {activity} in {town} — thank you. One question, which we think you
> can answer better than any guidebook: what is one thing near you that most visitors walk straight
> past? Not the famous sight — the one you would tell a friend about. A viewpoint, a bakery, a back
> road, the hour of the day when somewhere is at its best.
>
> Reply with the place and a sentence on why. The best answers go on the {town} page, in your
> words, with your name on them and a link to your listing.

### Proposed: validate by reply first, build a form second

**Round one needs no new infrastructure.** Providers reply by email or WhatsApp; each reply is
turned into a `picks:` entry by hand or by an agent, and reviewed in a PR like any content. This
tells us whether providers answer at all before anything is built to receive them.

**If they do, the form** — still without a database:

1. The mail carries a personal link, `world66.ai/pick/<CODE>`, using the provider's existing
   `outreach_code`. The code identifies them; no login, the same trust model as the QR highlight
   link.
2. The page asks three things: the place, why it is worth noticing, and the name to show.
3. Submitting opens a **GitHub issue** labelled `pick`, with a structured body: provider path,
   code, place, quote, name. The issue list is the inbox; git stays the only store.
4. An agent works through open `pick` issues — finds or creates the POI in the provider's
   location, adds the `picks:` entry — and opens one PR per batch. Review at merge, the same gate
   as all content. Issues close when the PR merges.

**The decision this needs: this repository is public.** A submission would be visible as an
issue the moment it is made, before anyone has reviewed it. The content is low-sensitivity —
businesses recommending places — and spam can be closed, but it is still unreviewed text under
someone's name. The alternatives are a small private repository used only as the inbox, or staying
with replies and no form at all.

## Don't

- Don't publish a pick someone did not write. The seed picks are credited to World66 for that
  reason.
- Don't pick the headline sight.
- Don't let a pick become an advert — a provider recommending their own tour is not a pick.
- Don't put a pick in a section subdirectory; it lives on the POI, and the POI lives flat in the
  location's folder.
