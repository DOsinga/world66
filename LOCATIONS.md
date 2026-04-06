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

The filter bar (All / Sight / Museum / Architecture / Neighbourhood) is rendered automatically from the `category` field on each POI. Recommended values:

| Category | Use for |
|----------|---------|
| `Sight` | Monuments, churches, ancient sites, viewpoints |
| `Museum` | Art galleries, history museums, science museums |
| `Architecture` | Buildings valued primarily for their design (not open as museums) |
| `Neighbourhood` | Districts and areas worth wandering — use sparingly; convert to `explore/` neighbourhood pages where possible |
| `Street` | Shopping streets, restaurant rows, market streets — named streets with a distinct character |
| `Square` | Squares, plazas, and open spaces that function as social hubs |
| `Park` | Parks, gardens, and green spaces |

#### POI stories

Things to do POIs can carry a `story:` field — a short historical anecdote or unexpected fact about the place. Rendered as a highlighted box labelled "A story" after the main body text.

Stories should be specific (a real incident or fact), surprising (not in a standard caption), and concise (2–4 sentences). Only add them when you know the anecdote is accurate.

```yaml
story: "The hooded figure dominating the square is the philosopher Giordano Bruno, burned alive on this spot on 17 February 1600."
```

For longer text, use a YAML block scalar (`story: >`).

#### Neighbourhood POIs

For large cities with an `explore/` section, `Neighbourhood` category POIs in `things_to_do/` should be converted to proper neighbourhood pages. See the Explore by Neighbourhood section below.

Other POIs tagged with `neighbourhood: "Name"` are automatically listed on the neighbourhood page, so a visitor reading the Jordaan page sees all restaurants and shops in the Jordaan without them being moved out of their sections.

The `neighbourhood:` value must match the neighbourhood page's `title` exactly (case-sensitive).

#### Streets, squares and parks

Named streets, squares, and parks are worth adding as POIs when they have enough character to be worth a traveller's time. Use categories `Street`, `Square`, or `Park`.

**City-level** — add to the relevant section (`shopping/`, `bars_and_cafes/`, `eating_out/`) with a `neighbourhood:` tag. Do this only if the street is a genuine destination on its own: a well-known market street, a famous nightlife strip, a park that draws people from across the city.

**Neighbourhood-level only** — store in `explore/<slug>/` as a POI (e.g., `explore/jordaan/bloemgracht.md`). These appear on the neighbourhood page but nowhere else. Use this for streets and squares that reward knowing about but are not city-level destinations: a beautiful canal that only locals seek out, a neighbourhood park, a local market street.

### Eating Out (`eating_out.md`)

Specific restaurants, trattorias, street food stalls. Each POI in `eating_out/`.

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
