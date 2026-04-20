# Location Pages — Guidelines

Location pages cover cities, towns, and regions. They are where travelers find specific, actionable information: what to see, where to eat, how to get around. This document defines what a good location page looks like.

## The overview page

The overview is the most important page. It should make someone want to visit — or at least understand the place. See STYLE.md for detailed guidance, but in short:

1. Open with what makes this place distinctive
2. Paint the picture — walk through the neighbourhoods, the highlights, the character
3. Be practical and opinionated — if something is great, say it's great
4. 3–5 paragraphs for a city, shorter for a small town

## Sections

Every location has sections as children. Sections are ordered alphabetically by filename slug — no `order` field needed. Not every location needs every section; a small town might only have an overview and a couple of sections.

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

Specific restaurants, trattorias, street food stalls.

### Bars and Cafes (`bars_and_cafes.md`)

Bars, cafes, gelaterias, and nightlife. Do not use a separate `nightlife` section — nightlife POIs go here.

### Shopping (`shopping.md`)

Only if there is real content — markets, shopping districts, notable shops.

### Day Trips (`day_trips.md`)

Day trip destinations should be real locations in the hierarchy, not POIs. Use `linked_locations:` in the section frontmatter to list their paths:

```yaml
---
title: "Day Trips"
type: section
linked_locations:
  - europe/italy/lazio/frascati
  - europe/italy/lazio/ostiaantica
---

Brief overview of day trip options from the city.
```

The template renders these as a table linking to the real location pages.

### Beaches (`beaches.md`)

Only where relevant (coastal cities).

### When to Go (`when_to_go.md`)

Climate, seasons, best times to visit, events worth timing a trip around.

### Getting There (`getting_there.md`)

How to arrive — airports, train stations, bus connections.

### Getting Around (`getting_around.md`)

Transport within the city — metro, buses, taxis, walking, bike rental.

### Books (`books.md`)

Novels and literature that help understand the place — its history, its people, its character. Not travel guides, not history books. The test: would a traveller who reads this understand the city differently?

Each book is a POI in `books/` with `author:` and optionally `isbn:`. Aim for 3–5 books per city.

```yaml
---
title: "My Brilliant Friend"
type: poi
author: "Elena Ferrante"
isbn: "978-1609450786"
---

The first of Ferrante's four Neapolitan novels...
```

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

This POI will appear on the Things to Do page, on the South Beach neighbourhood page, and can be filtered by Museum. The `art_deco` tag links it to the Art Deco District POI's page if one exists.

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

```yaml
# A restaurant in South Beach
tags:
  - eating_out
  - south_beach
  - restaurant
neighbourhood: South Beach    # display label in listings
```

### Descriptive tags

Beyond section, category, and neighbourhood tags, add descriptive tags for any notable characteristic of the POI. If a POI with that slug exists, the tag becomes a link. Common examples:

- Architectural styles: `art_deco`, `mediterranean_revival`
- Activities: `swimming`, `cycling`, `wildlife`
- What you'll find: `restaurant`, `bar`, `cafe`, `gallery`, `garden`, `park`, `theatre`, `sport`

Be generous with tags — they help visitors discover POIs through multiple paths. A neighbourhood POI for Wynwood might carry `things_to_do`, `neighbourhood`, `art`, `restaurant`, `bar`, `gallery` because those are what define the area.

## Coordinates

Every POI must have `latitude` and `longitude`. Without them the POI won't appear on the map. Precision to 4 decimal places is enough (~10m accuracy).

```yaml
latitude: 41.9009
longitude: 12.4833
```

Do not publish a POI without coordinates. If you cannot determine them, leave the file out.

## Principles

- **The overview is king.** A great overview with no sections is better than a thin overview with ten empty sections.
- **Delete empty sections.** A page that says "We currently have no X" is worse than no page at all.
- **Quality over completeness.** A city with a good overview, solid things to do, and a couple of well-written sections is well-served. Don't create stub sections just to fill the list.
- **Link generously.** Every neighbourhood, nearby city, or day trip mentioned should link to its page if one exists.
- **Be specific.** Name the restaurant and the dish. Include the address, the hours, the price. Vague advice is useless.

## Reference implementations

| City | Path | Notes |
|------|------|-------|
| Milan | `europe/italy/lombardia/milan` | Original `things_to_do` implementation |
| Rome | `europe/italy/lazio/rome` | Category filters, story fields, neighbourhood POIs |
| Florence | `europe/italy/tuscany/florence` | Category filters |
| Venice | `europe/italy/veneto/venice` | Category filters |
| Naples | `europe/italy/campania/naples` | Category filters |
