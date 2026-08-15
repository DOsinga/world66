# List Enrichment Task

## Goal

Bring a country up to the list targets described in [LISTS.md](../../LISTS.md) — read that file in full before starting, it defines the frontmatter schema, the "surprising" quality bar, and the target count per level. This task is about filling the gaps for one country at a time: the country itself, its regions, its features, and its big/second-tier cities.

**Read LISTS.md's targets table again right now.** Country ~5, region ~3, feature 1–2, big city ~5, second-tier city 1–2, smaller city/town 0. The United Kingdom (`content/europe/unitedkingdom/`) is the worked example — look at its existing lists (`quirky_uk_bookshops.md`, `quirky_uk_pubs.md`, `wild_uk_beaches.md`, and the ones nested under `england/`, `england/london/`, `england/cornwall/`) for the tone and format to match, but check its current counts before assuming it's already at target — it may still have gaps itself.

**Quality beats quantity, same as everywhere else in this codebase.** A country with 3 genuinely surprising lists is better than one padded to 5 with generic ones. Never invent a list just to hit a number, and never invent an item to fill out a weak list.

## For each country in the batch

### 1. Audit the current state

```bash
# All existing lists anywhere under this country
grep -rl "^type: list" content/<country_path>/ --include="*.md"
```

For each one found, note which level it lives at (country top-level directory, a `loc_type: region` directory, a `loc_type: feature` directory, or a `loc_type: city` directory) so you know what's already been done.

### 2. Map out the tiers

- **Country**: the country's own top-level directory.
- **Regions**: every `loc_type: region` directory directly under the country.
- **Features**: every `loc_type: feature` directory (named areas like Cornwall or the Lake District — these can sit under a region or directly under the country).
- **Big city**: the country's capital or single clearest largest/most internationally famous city. Usually exactly one. Use real-world knowledge of city size and significance, not the site's tourism `score` — a small, beautiful town can outscore a country's largest city on this site's scale, but it isn't "big" for this purpose.
- **Second-tier cities**: the country's other nationally significant cities — usually 3–10 of them depending on the country's size. Real, sizeable urban centers with real cultural weight, not just high-scoring tourist towns.
- **Everything else**: smaller cities and towns get no dedicated list, however charming or high-scoring. Their POIs remain eligible as *items* on a list at a higher level.

Getting this classification right matters more than getting the exact list counts right — misjudging a country's second city as "smaller" (or vice versa) will throw off the whole rest of the pass. If you're unsure, err toward fewer second-tier cities rather than more: a shorter, well-chosen set is better than list-fatigue from a dozen mediocre city-level lists.

### 3. Compute the gap and brainstorm ideas

For each level that's under its target, brainstorm 2–3x as many list ideas as you'll actually need, then keep only the ones that pass LISTS.md's "surprising" bar. For each candidate idea, sanity-check before committing to it:

- **Can I name at least 5 real, specific, already-documented places that fit this theme right now?** Search the content tree (`grep -rl` for the relevant tag or keyword, or just your own knowledge of what's already written for this country) before assuming a theme works.
- **Does a similar list already exist at a different level for this country?** Don't create a country-wide "Best Castles" if a region under it already has one covering the same castles — either merge, narrow the angle, or drop the idea.
- **Would a well-traveled local for this country be even slightly surprised by the title?** If not, sharpen the angle (narrower theme, a genuine contradiction, a real oddity) or drop it.

### 4. Source the items

Prefer existing content. For each list you're building:

1. Search the tree for POIs/locations that already fit the theme (`grep -rl` on tags, titles, or snippets; browse the relevant city/region directories).
2. If you can find 5–8 strong, real fits, you're done — just gather the exact content paths.
3. If you're one or two short of a genuinely good list (not padding — a real gap), research and add the missing POI(s) the normal way: a real, named, visitable place, with accurate coordinates (verify via OpenStreetMap/Wikivoyage the same way `major_city_neighborhoods` does), a `score` (1.0–10.0, calibrated against similar POIs), and a `snippet`. Give it a hero image via the `find-photo` skill if you can find one on Wikimedia Commons — lists borrow their cover image from the first item that has one, so an image-less item anywhere in the list is fine, but an image-less list (every item lacking one) is a weak list.
4. If you can't reach 5 solid real items even after research, the idea doesn't work for this country yet — drop it and try a different angle rather than forcing it.

### 5. Write the list page

Create `content/<path-to-level>/<slug>.md`:

```yaml
---
title: N <Adjective> <Topic>
type: list
score: 8.0
snippet: The one vivid, specific hook — not a description of the format
items:
  - path/to/item/one
  - path/to/item/two
  - path/to/item/three
  - path/to/item/four
  - path/to/item/five
---

First paragraph: what this list is really about, naming 2-3 of the most
vivid/surprising entries to earn the reader's attention.

Second paragraph: the throughline — what these places share that a generic
list on the same rough topic wouldn't have captured.
```

- Put the list file in the directory of the level it belongs to (country top-level dir, the region's dir, the feature's dir, or the city's dir) — same convention as a section file living alongside its parent.
- Slug: short, descriptive, lowercase with underscores (`quirky_uk_bookshops`, `strangest_sights_in_cornwall`).
- 5–8 items, ordered with the best/most surprising near the top since that's the visual rank shown on the page.

### 6. Add back-references

For every item you used, add (or extend) its `lists:` field:

```yaml
lists:
  - path/to/the/list
```

A page can be on more than one list — extend the array rather than overwrite it if `lists:` already has entries.

### 7. Verify

```bash
python3 manage.py check
python3 tools/linter.py
```

The linter's `list_items` and `lists_backref` checks catch any path in `items:`/`lists:` that doesn't resolve — fix any it reports before moving on.

Spot-check on the dev server: the list page renders the ranked grid with a real cover image (borrowed from an item) and a sidebar map with a marker per item; the list's parent location page(s) show the "Featured list" callout at the bottom (highest-scored list in that directory) with any others linked below it; at least one item shows the "Featured on" badge.

### 8. Mark done and commit

```bash
python3 tools/mark_done.py list_enrich content/<country_path>.md
```

One commit per country: `Lists: <Country> — N new lists`

## Checklist before committing each country

- [ ] Read LISTS.md's targets table and matched this country's structure against it (country/region/feature/big city/second-tier city)
- [ ] Every new list has 5–8 items, no invented items, no list forced to hit a count
- [ ] Every list's title/snippet passes the "would a local be surprised" test — no generic "Top Museums in X" ideas shipped
- [ ] No two lists (at any level in this country) cover the same ground
- [ ] Every `items:` path resolves (linter `list_items` clean)
- [ ] Every item used has a matching `lists:` back-reference (linter `lists_backref` clean)
- [ ] No list has an `image:` field of its own
- [ ] Any new POI created to complete a list has a real, verified coordinate, a `score`, and a `snippet` — no fabricated places
- [ ] `python3 manage.py check` and `python3 tools/linter.py` both clean
- [ ] Dev-server spot check: list page renders with cover image + map; parent location(s) show the featured-list callout

## Reference implementation

`europe/unitedkingdom` — the pilot for this task (see PR #2236 and follow-ups). Check its current list count against the targets before assuming it's finished; it may still need more country- and region-level lists, and second-tier UK cities (Edinburgh, Glasgow, Manchester, Birmingham, Liverpool, Bristol, Leeds, Newcastle, Cardiff, Belfast) had none as of this task's creation.
