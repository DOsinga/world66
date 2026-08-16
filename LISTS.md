# Lists

A list is a curated, ordered "top N" page — `type: list` — that names its members explicitly. It's a cross-cutting complement to the normal hierarchy: instead of grouping by geography (a country's cities, a city's POIs), a list groups by theme across the tree ("Quirky UK Bookshops" pulls from Northumberland, Wales, London, and the Scottish Highlands in one page).

A list has no children of its own and does no querying or tag aggregation. Its `items:` field is the single source of truth for its membership, and it never changes unless someone edits the page.

## Frontmatter

```yaml
---
title: 6 Quirky UK Bookshops
type: list
score: 8.0
snippet: From a converted railway station to a champagne-fuelled reading spa, the
  UK's most characterful independent bookshops
items:
  - europe/unitedkingdom/england/north_east/northumberland/alnwick/barter_books
  - europe/unitedkingdom/wales/hay_on_wye/richard_booths_bookshop
  - europe/unitedkingdom/england/london/daunt_books
  - europe/unitedkingdom/england/south_west/bath/mr_bs_emporium
  - europe/unitedkingdom/england/south_east/oxford/blackwells_bookshop
  - europe/unitedkingdom/scotland/lochinver/achins_bookshop
---
```

- **`title`** — put the count in the title ("6 Quirky UK Bookshops", not "Quirky UK Bookshops"). Readers want to know the length before they click.
- **`items`** — a list of content paths (POIs or locations, anywhere in the tree). Order matters — it's the rank shown on the page. 5–8 items is the normal range; fewer than 5 feels thin, more than 8 stops being a tight, scannable list.
- **`score`** — same 1.0–10.0 scale as everything else, used to pick which list gets the "Featured list" callout when a location has more than one. `8.0` is a reasonable default for a solid list; score it like you would a strong POI.
- **`snippet`** — the hook, not a description of the format. Name the single most surprising or vivid thing in the list, not "a collection of X" or "top places to Y."
- No `image` field — a list borrows the image from the first item in `items:` that has one, and so does the featured-list callout on its parent location page. Order `items:` with that in mind if the best photo isn't on the first entry you'd otherwise pick.

### Back-references

A page that appears on one or more lists can carry a `lists:` field so its own page shows a small "Featured on" badge:

```yaml
lists:
  - europe/unitedkingdom/quirky_uk_bookshops
```

This is purely display — manually kept in sync, not derived from the lists that reference the page. When you add a page to a list's `items:`, add the list back to that page's `lists:` in the same commit.

## What makes a good list

**Be more creative than the obvious angle.** "5 Great Places for Afternoon Tea" is a fine *idea* but a boring *list* — anyone could guess it exists. The bar is: would a well-traveled local raise an eyebrow and think "oh, I didn't expect that one" at least once scrolling through it? Push toward the specific, the odd, the contradictory:

- **Good**: "Quirky UK Bookshops" (a champagne-and-recommendations shop, a former railway station, a hydraulic-jacked cavern), "Wild & Deserted UK Beaches", "Strangest Sights in Cornwall" (a shipwreck festival, a labyrinth, a smugglers' cove).
- **Weak**: "Top Museums in London", "Best Restaurants in Paris", "Beautiful Beaches in Thailand" — true, but generic enough that they don't need a human's judgment to write.

A useful test: if the title alone could apply to fifty different guidebooks with the same five obvious entries, it's not surprising enough yet. Narrow the angle (not "London Markets" but "London's Underground Markets"), find the contradiction (not "Beautiful Beaches" but "Beaches You Can Only Reach on Foot"), or lean into a genuine oddity (a museum in a disused public toilet, a pub with no bar).

**Every item must be real and already visitable.** Don't invent a place to complete a theme. If you can't find a sixth genuinely good item, ship a list of five rather than pad it with a weak one.

**Write two short paragraphs of body text**, same voice as everywhere else on the site (see STYLE.md): the first sets up what the list is really about and gestures at 2–3 of the most vivid entries; the second names the throughline — what these places share that a generic list wouldn't capture.

## How many lists a place should have

Lists take real curatorial effort — writing one badly, or one nobody would click, is worse than not writing it. Use this as a target, not a quota to fill mechanically:

| Level | Target |
|---|---|
| Country | ~5 lists |
| Region (`loc_type: region`) | ~3 lists |
| Feature (`loc_type: feature`) — a named area like Cornwall or the Lake District | 1–2 lists |
| Big city — a country's capital or clear largest/most famous city | ~5 lists |
| Second-tier city — a nationally significant city, but not the country's flagship | 1–2 lists |
| Smaller city or town | 0 dedicated lists |

A place with no dedicated list is not excluded from the system — its POIs and its own page are still fair game as *items* on a country, region, or big-city list. A small town with one truly odd, list-worthy POI belongs in someone else's list, not as the site of its own thin one.

"Big" vs. "second-tier" vs. "smaller" is a judgment call, not a formula — this site's `score` field measures tourist appeal, not city size, and a tiny, beautiful town (Bath, York, Grasmere) will often out-score a big, unglamorous one (Bristol, Leeds). Use real-world knowledge of which cities are actually large, nationally significant urban centers. For the United Kingdom, that reads as:

- **Big**: London.
- **Second-tier**: Edinburgh, Glasgow, Manchester, Birmingham, Liverpool, Bristol, Leeds, Newcastle, Cardiff, Belfast.
- **Smaller / no dedicated list**: everywhere else, including places that score very highly for charm (Bath, York, Oxford, Cambridge, Keswick, St Ives) — real destinations, just not list-hosting ones. Their best POIs are exactly the kind of thing a country- or region-level list should pull in.

The United Kingdom is the reference example (see `content/europe/unitedkingdom/`) — as of this writing it's a work in progress against these targets, not a finished one; check current counts before assuming it's fully filled out.

## Don't

- Don't create a list with fewer than 5 items or more than 8.
- Don't invent an item to hit a target count.
- Don't write a list whose title describes a format anyone could guess ("Top Restaurants in X").
- Don't duplicate an existing list's angle at a different geographic level (a country-wide "Best Castles" and a region-level "Best Castles in the North" covering the same handful of castles).
- Don't give a small town its own list just to hit a quota — feature its best POI on a broader list instead.
- Don't add an `image:` field to a list — it always borrows from the first item.
