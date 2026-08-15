# Location Pages — Guidelines

Location pages cover cities, towns, and regions. They are where travelers find specific, actionable information: what to see, where to eat, how to get around. This document defines what a good location page looks like.

## Location types (`loc_type`)

Every page with `type: location` also carries a `loc_type` field that describes what kind of place it is. This is what distinguishes a city from a region, a national park from a city. Without it, batch workflows and rendering can't tell a leaf settlement apart from a regional container.

| Value | Use for | Example paths |
|-------|---------|---------------|
| `continent` | The seven top-level continent pages | `europe`, `asia` |
| `country` | Sovereign states and territories with their own page | `europe/france`, `asia/japan` |
| `region` | The grouping level below a country in large countries. For the US these are states; elsewhere they may be editorial or administrative groupings. | `northamerica/unitedstates/california`, `europe/france/south`, `europe/italy/tuscany` |
| `city` | Cities, towns, villages — actual settlements | `europe/france/paris`, `asia/india/jaipur` |
| `feature` | A named area or attraction that is a destination in itself but not a settlement: national parks, gorges, coastlines, named tourist regions, archipelagos, archaeological sites. | `europe/italy/liguria/cinque_terre`, `northamerica/unitedstates/wyoming/yellowstone`, `asia/cambodia/angkorwat` |
| `island` | An island with more than one real destination on it — a main town plus outlying villages, or several towns of roughly equal weight. Works exactly like `feature`: it can have its own POIs, and its towns link to it via `tags`, never by nesting. Use plain `city` instead for an island that is really just one settlement. | `europe/croatia/hvar`, `europe/greece/cyclades/santorini` |

## Hierarchy

Most location paths follow this shape:

```text
continent/country/[region]/city_or_feature
```

Regions are optional and should be used only for countries large enough to need grouping, roughly 100 or more cities and features. If a country uses regions, its ordinary cities and features should live inside one. Regions contain child cities, child features, and their own POIs for things that belong to the wider area rather than any one city.

There are two known exceptions:

- Globally recognised capitals and major cities may sit directly below their country even when that country uses regions. Current examples include Paris, Berlin, Hamburg, and Tokyo.
- The United Kingdom has constituent countries directly below `unitedkingdom/`, and England has its own sub-regions such as `cumbria` and `eastern_england`. Treat this as a known structural exception, not as a hierarchy violation.

Regions are named for what travelers recognise. For the United States, that means states such as `california` and `texas`; for France and Italy, it may mean editorial or administrative groupings such as `south`, `tuscany`, or `lazio`. The `loc_type` for all of these is `region`.

Cities are leaf-level settlements: they have sections, POIs, and sometimes neighbourhoods, but they do not contain other cities or features as child locations.

Features are named areas that are destinations in their own right but not settlements: Cinque Terre, the Ardèche gorge, Normandy, Côte d'Azur, Loire Valley, Big Sur, Yellowstone. Features can have their own POIs. Nearby cities link to a feature by adding the feature slug to `tags`:

```yaml
# content/europe/italy/liguria/riomaggiore.md
title: Riomaggiore
type: location
loc_type: city
tags:
  - cinque_terre
```

If a location is tagged `loc_type: region` but sits inside another region, it is usually a feature. The one-level region rule means places like Loire Valley, Côte d'Azur, Ardèche, and Cinque Terre should be features unless they are the country's top-level grouping.

**Never mix nesting and tagging for the same parent.** A `region` contains its child cities and features as files in its own directory. A `feature` or `island` never does — its children are always siblings elsewhere in the hierarchy, connected only by `tags`. Don't let a `type: location` file live inside a feature's or island's own directory just because it happens to be geographically close; that directory is for the feature/island's own POIs and sections only. If you find one there, it means either the child was nested under the old region model before the parent was retyped, or someone reached for the nearby directory as a shortcut — either way, move the location out to its correct place in the hierarchy and add the `tags` link instead of leaving it nested. A parent that mixes both patterns makes it unclear, at a glance, whether a given child is discoverable through the normal tag-based mechanism or not.

City-states (Monaco, Vatican City, Singapore) are typed `country` at the country-depth file and `city` only if they have a separate city page below.

Neighbourhoods and districts within cities are not locations — they use `type: neighbourhood` and live in the parent city's directory. See [Neighbourhood tags](#neighbourhood-tags) below.

## The overview page

The overview is the most important page. It should make someone want to visit — or at least understand the place. See STYLE.md for detailed guidance, but in short:

1. Open with what makes this place distinctive
2. Paint the picture — walk through the neighbourhoods, the highlights, the character
3. Be practical and opinionated — if something is great, say it's great
4. 3–5 paragraphs for a city, shorter for a small town

## The snippet

Every location should have a `snippet:` field in its frontmatter — a one-line definition of the place that renders below the title on the location page, and is used as the blurb in destination cards, search results, and meta descriptions. It's the same field POIs use, but the content rule is different because locations are categorically broader.

**The rule:** what kind of place + the single thing that makes it itself.

Not a list of attractions. Not "things you can do here." One identifying truth, optionally with a second clause that adds geography, era, or atmosphere.

- **Target length:** 12–20 words. Hard cap 25. If it doesn't fit, the lede paragraph is doing the work anyway.
- Lead with the **kind of place** (capital, port city, mountain region, archipelago, imperial city, wine region…) so it reads as a definition.
- Add **one** distinguishing fact. Resist the temptation to list two.
- No verbs of address ("explore", "discover", "visit"), no hollow superlatives ("amazing", "must-see").
- Should still make sense out of context — in a search result, a tooltip, a card on a continent page.

Examples:

- **Paris** — Romantic French capital of art, food, and Haussmann boulevards, divided by the Seine into the grand Right Bank and quieter Left
- **Tokyo** — Vast, orderly Japanese megacity where neon entertainment districts sit beside wooden shrines and the world's busiest commuter rail network
- **Kyoto** — Japan's old imperial capital, dense with Zen temples, moss gardens, and tea houses, ringed by forested hills
- **Reykjavik** — Tiny North Atlantic capital and gateway to Iceland's volcanic interior, with geothermal pools and long subarctic summer light
- **Patagonia** — Wind-scoured wilderness of glaciers, granite spires, and sheep estancias spanning the southern tip of Argentina and Chile
- **France** — Europe's archetypal country: Atlantic and Mediterranean coasts, alpine villages, Loire châteaux, and the wine regions that define the western table

## Magazine teaser

An optional `magazine_teaser:` field feeds the magazine-view card grid (the alternate, image-led browsing layout available on country/region/feature pages and cities with an imaged neighbourhood strip — see `guide/views.py::_magazine_teaser`). It's a hook, not a definition: one or two vivid sentences that make someone want to click through, distinct from `snippet`'s terse "kind of place + one fact."

Purely additive — pages without it fall back to the first paragraph of the body, then to `snippet`, so there's no backlog to clear before the feature works. Add it selectively, where you can write something better than the automatic fallback. Same rule as everywhere else: never invent a fact to make the hook punchier.

```yaml
magazine_teaser: "Stand on a flat-topped cliff 604 metres above a fjord, or wedge yourself onto a boulder a kilometre higher still — Lysefjord asks for a head for heights."
```

## Quick facts

A location's frontmatter may carry a `quick_facts:` block. Only add this if the city is a major travel destination and it's easy to find good facts. Never fabricate things.

**The rule:** four facts per location — **two hard-data facts and two fun-but-true facts** — written as clean `key: value` pairs.

- **Two hard-data facts.** Objective, verifiable figures the reader expects up top: population, currency, area, elevation, founding year, official language.
- **Two fun-but-true facts.** A genuine, checkable curiosity that makes the place memorable — a record it holds, an unusual superlative, a quirk of geography or history. Fun, but never invented.

Format rules:

- Each entry is a **short attribute label → crisp value**. The key is the label (`Population`, `Founded`, `Highest Point`); the value is the answer (`2.1 million`, `1632`, `Mount Teide, 3,715 m`).
- **Keys are distinct** within a location — no two facts share a label.
- **Every value stands on its own.** Don't split one fact across the key and value as a continuation: write `Canals: 165 km, more than Venice`, never `More Canals: Than Venice`. The key names an attribute; the value is a complete answer.
- Keep values tight — a figure plus at most a short qualifying clause, never a sentence.

Example (Amsterdam):

```yaml
quick_facts:
  Population: 920,000
  Founded: c. 1275, as a dam on the Amstel
  Canals: 165 km — more than Venice
  Bicycles: 1 Million - more than residents
```

Two hard-data facts (population, founding), two fun-but-true (the canal length, the bicycle count), each a distinct label with a self-contained value.

## Sections

Every location has sections - they are separate md files in the location folder. Sections are ordered alphabetically by filename slug — no `order` field needed. Not every location needs every section; a small town might only have an overview and a couple of sections.

### Things to Do (`things_to_do.md`)

All sights, museums, galleries, and notable neighbourhoods go in a single `things_to_do` section. Do not use separate `sights` and `museums` sections.

The filter bar is rendered automatically from POI tags. See [How tags work](#how-tags-work) below for details.

#### POI stories

Things to do POIs can carry a `story:` field — a short historical anecdote or unexpected fact about the place. Rendered as a highlighted box labelled "A story" after the main body text.

Stories should be specific (a real incident or fact), surprising (not in a standard caption), and concise (2–4 sentences). Only add them when you know the anecdote is accurate.

```yaml
story: "The hooded figure dominating the square is the philosopher Giordano Bruno, burned alive on this spot on 17 February 1600."
```

For longer text, use a YAML block scalar (`story: >`).

### Eating Out (`eating_out.md`)

Specific restaurants, trattorias, street food stalls, gelaterias.

### Bars and Cafes (`bars_and_cafes.md`)

Bars, cafes, and nightlife. Do not use a separate `nightlife` section — nightlife POIs go here.

### Shopping (`shopping.md`)

Only if there is real content — markets, shopping districts, notable shops.

### Day Trips (`day_trips.md`)

A day trip is a destination in its own right, so every entry is a **linked location**, never a POI:

- **A town or city** must be a **link** to its destination page, listed in `linked_locations:` (and linked inline in the prose). If the town has no page yet, create one. Never leave a town as a POI inside the city directory — that shadows the real page.
- **A larger area, valley, region, or natural feature** (a wine region, a peninsula, a sound, a touring route) should be a **`loc_type: feature` destination page** in the right place in the hierarchy, then linked the same way.
- **A single nearby attraction** — a convent 10 km out, a beach 15 km south, a single ruin, a zoo, a house museum — is just a normal POI on the city's `things_to_do` list; don't tag it `day_trips`. If it is really a destination in its own right, promote it to a `loc_type: feature` page and link it.

The one rule: **`day_trips` entries are always linked locations; never tag a POI `day_trips`.** The linter enforces this (the `day_trip_poi` check).

Use `linked_locations:` in the section frontmatter to list the destination paths:

```yaml
---
title: "Day Trips"
type: section
linked_locations:
  - europe/italy/lazio/frascati
  - europe/italy/lazio/ostiaantica
---

Brief overview of day trip options, linking each destination inline.
```

The template renders the linked locations as a destination card grid.

### Beaches (`beaches.md`)

Only where relevant (coastal cities).

### When to Go (`when_to_go.md`)

Climate, seasons, best times to visit, events worth timing a trip around.

For non-country locations (regions, cities, features), only add a `when_to_go` section when the place is **substantially different** from its parent country — a high-altitude city, a tropical island off a temperate coast, a place with unique events worth timing a visit around. Amsterdam doesn't need its own when_to_go when the Netherlands has one; Quito does, because the equatorial mountains override Ecuador's general climate story.

### Getting There (`getting_there.md`)

How to arrive — airports, train stations, bus connections.

### Getting Around (`getting_around.md`)

Transport within the city — metro, buses, taxis, walking, bike rental.

### Books (`books.md`)

Novels and literature that help understand the place — its history, its people, its character. Not travel guides, not history books. The test: would a traveller who reads this understand the city differently?

Write 3–5 recommendations inline in `books.md`. Each one should name the book and author, say what it's about, and explain why a traveller would want to read it. Don't create a `books/` subdirectory with POI entries — books are not points on the map.

## Sections that don't belong on location pages

- `sights.md`, `museums.md` — replaced by `things_to_do`
- `nightlife.md` — replaced by `bars_and_cafes`
- `practical_informat.md`, `7_day_itinerary.md`, `history_1.md`
- `top_5_must_dos.md`, `budget_travel_idea.md`, `family_travel_idea.md`
- `festivals.md` — content belongs in `when_to_go`
- `cybercafs.md`, `webcams.md`

## How tags work

Tags are the central organising mechanism for POIs. Every POI has a `tags` list in its frontmatter, and tags serve three purposes simultaneously:

1. **Section membership** — a tag matching a section slug puts the POI on that section's page
2. **Neighbourhood membership** — a tag matching a neighbourhood slug puts the POI on that neighbourhood's page
3. **Filter categories** — certain tags become buttons in the filter bar on section pages

A single POI typically carries several tags. For example, a museum in South Beach that is housed in an Art Deco building:

```yaml
tags:
  - things_to_do
  - south_beach
  - museum
  - art_deco
```

This POI will appear on the Things to Do page, on the South Beach neighbourhood page, and can be filtered by Museum. The `art_deco` tag is for filtering.

### Section tags

The first tag usually determines which section the POI belongs to. Use the slug of the section file:

| Tag | Section |
|-----|---------|
| `things_to_do` | Things to Do |
| `eating_out` | Eating Out |
| `bars_and_cafes` | Bars and Cafes |
| `shopping` | Shopping |

### Category tags

These tags become filter buttons on section pages. The recognised category tags are:

| Tag | Use for |
|-----|---------|
| `sight` | Monuments, squares, churches, viewpoints, parks, memorials |
| `museum` | Art galleries, history museums, science museums |
| `architecture` | Buildings valued primarily for their design |
| `neighbourhood` | Districts and areas worth wandering |
| `restaurant` | On eating_out POIs |
| `bar` | On bars_and_cafes POIs |
| `market` | Markets, farmers markets |

### Neighbourhood tags

For large cities, create neighbourhood POIs (with `type: neighbourhood` in the tags). Then tag other POIs with the neighbourhood's **slug** to make them appear on the neighbourhood page. For example, if you have a `south_beach.md` neighbourhood POI, tag restaurants and sights in that area with `south_beach`.

The `neighbourhood:` frontmatter field is a separate display-only property — it shows the neighbourhood name next to the POI in listings. But the **tag** is what actually collects the POI onto the neighbourhood page.

When a large city has over 3 neighbourhoods they should all have images, so they render nicely.

```yaml
# A restaurant in South Beach
tags:
  - eating_out
  - south_beach
  - restaurant
neighbourhood: South Beach    # display label in listings
```

### Descriptive tags

Beyond section, category, and neighbourhood tags, add descriptive tags to POIs for any notable characteristic. If a POI with that slug exists, the tag becomes a link. Common examples:

- Architectural styles: `art_deco`, `mediterranean_revival`
- Activities: `swimming`, `cycling`, `wildlife`
- Cuisine: `cuban`, `seafood`, `peruvian`
- What the place is: `cafe`, `gallery`, `garden`, `park`, `theatre`, `sport`, `historic_house`

Be generous with tags on POIs — they help visitors discover places through multiple paths.

**Neighbourhood POIs themselves should only carry `things_to_do` and `neighbourhood` as tags.** The neighbourhood page collects its content from other POIs that carry the neighbourhood's slug as a tag. Do not put descriptive tags like `restaurant` or `bar` on the neighbourhood POI — those belong on the actual restaurant and bar POIs within the neighbourhood.

## Coordinates

Every POI must have `latitude` and `longitude`. Without them the POI won't appear on the map. Precision to 4 decimal places is enough (~10m accuracy).

```yaml
latitude: 41.9009
longitude: 12.4833
```

Do not publish a POI without coordinates. If you cannot determine them, leave the file out. Don't make up coordinates. Check and double check.

A `neighbourhood` page also needs `latitude` and `longitude` — this is the pin for its card on the city map. Give it the **centre of the district**, and make sure it is not identical to one of its POIs. The map deduplicates markers that share the exact same coordinate, so a neighbourhood whose centre lands on top of one of its own POIs will silently drop off the map. (This is a placement bug, not a tagging one — the neighbourhood's POIs still collect correctly via its slug tag.)

## POI scores

Every POI must have a `score` field in its frontmatter. Scores are floats from `1.0` to `10.0` and are used to order POI lists within a location, with the most important places first.

Calibrate scores against the other POIs in the same parent location. Before adding or changing a POI score, look at the existing scores for that location and place the new POI into that local lineup. The exact global score of a Paris museum versus an Amsterdam museum matters less than whether each city page presents its own strongest sights first.

Use this scale:

| Score range | Meaning |
|-------------|---------|
| `9.0`-`10.0` | World-class or essential for the place; worth travelling far to see |
| `8.0`-`8.9` | Headline attraction; a major reason to include the location in a trip |
| `7.0`-`7.9` | Strong second-tier sight; clearly worth making time for |
| `6.0`-`6.9` | Solid but more selective; good for a third day or to fill an afternoon |
| `5.0`-`5.9` | Minor, niche, or nice-to-have |
| `< 5.0` | Low priority; mainly for completists or people already nearby |

```yaml
score: 7.4
```

### Location scores (`loc_type: city` / `feature` / `island`)

Cities, features, and islands — `type: location` pages below the region level — also carry a `score` on the same `1.0`-`10.0` scale as POIs, so destinations and the sights within them sort consistently everywhere they're listed together.

These scores aren't hand-picked one at a time the way POI scores are. They come from `tools/rank_locations.py`, which repeatedly asks Claude to order small batches of destinations from best to worst, fits a Plackett-Luce model to the accumulated pairwise rankings, and percentile-maps the result onto the same score distribution as scored POIs (`POI_SCORE_QUANTILES` in that file). This keeps location and POI scores comparable without manually comparing every location against every POI.

A brand-new city/feature/island page won't have a score until it's been through that process. Don't leave it unscored in the meantime — either:
- run `python tools/rank_locations.py discover`, then enough `run --rounds` against the Claude API to get it compared, then `apply`; or
- if that's not practical right now, hand-calibrate a score by comparing the new page against sibling locations in the same parent directory, the same way you would for a POI.

**Countries, regions, and continents are scored on a separate, older `0.0`-`1.0` scale** that predates this system and is unrelated to it — don't try to "fix" a country score that looks low next to a city's `7.4`. Only `city`/`feature`/`island` locations and POIs use the `1.0`-`10.0` scale.

## Sources

The `sources` field records reference URLs used when writing or enriching a page. Add it to the frontmatter of any location page where a useful external reference exists. It is a list, so multiple sources can be recorded. Any time we discover a source, add it to the list for future reference, both for pois & locs

```yaml
sources:
  - https://en.wikivoyage.org/wiki/Hubei
  - https://en.wikipedia.org/wiki/Hubei
```

## Principles

- **The overview is king.** A great overview with no sections is better than a thin overview with ten empty sections.
- **Delete empty sections.** A page that says "We currently have no X" is worse than no page at all.
- We need section.md files to show the pois for a section. In order for pois tagged things_to_do to show up in the guide, there needs to be a section.
- **Quality over completeness.** A city with a good overview, solid things to do, and a couple of well-written sections is well-served. Don't create stub sections just to fill the list.
- **Link generously.** Every neighbourhood, nearby city, or day trip mentioned should link to its page if one exists.
- **Be specific.** Name the restaurant and the dish. Include the address, the hours, the price. Vague advice is useless.

## Reference implementations

| City | Path | Notes |
|------|------|-------|
| Milan | `europe/italy/lombardia/milan` | Original `things_to_do` implementation |
| Amsterdam | `europe/netherlands/amsterdam` | Category filters, story fields, neighbourhood POIs |
| Paris | `europe/france/Paris/  | Category filters, story fields, neighbourhood POIs |
