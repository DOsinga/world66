# Location Pages — Guidelines

Location pages cover cities, towns, and regions. They are where travelers find specific, actionable information: what to see, where to eat, how to get around. This document defines what a good location page looks like.

## Location types (`loc_type`)

Every page with `type: location` also carries a `loc_type` field that describes what kind of place it is. This is what distinguishes a city from a region, a national park from a city. Without it, batch workflows and rendering can't tell a leaf settlement apart from a regional container.

| Value | Use for | Example paths |
|-------|---------|---------------|
| `continent` | The seven top-level continent pages | `europe`, `asia` |
| `country` | Sovereign states and territories with their own page | `europe/france`, `asia/japan` |
| `region` | The single grouping level directly below a country in large countries. For the US these are states; for other countries they are editorial or administrative groupings. Regions **contain** cities and features. | `northamerica/unitedstates/california`, `europe/france/south`, `europe/italy/tuscany` |
| `city` | Cities, towns, villages — actual settlements | `europe/france/south/paris`, `asia/india/delhi` |
| `feature` | A named area or attraction that is a destination in itself but not a settlement: national parks, gorges, coastlines, named tourist regions, archipelagos, archaeological sites. Features have their own POIs and cities nearby can tag into them. | `europe/france/south/ardeche`, `europe/italy/liguria/cinque_terre`, `northamerica/unitedstates/wyoming/yellowstone` |

City-states (Monaco, Vatican City, Singapore) are typed `country` at the country-depth file and `city` only if they have a separate city page below.

Neighbourhoods and districts within cities are not locations — they use `type: neighbourhood` and live in the parent city's directory. See [Neighbourhood tags](#neighbourhood-tags) below.

## The region level

Regions are the single intermediate level between a country and its cities. Use them for countries that have enough locations to warrant grouping (roughly 100 or more cities and features).

**The rule is absolute: if a country uses regions, every city and every feature lives inside a region. No cities or features sit directly at the country level.**

For the United States, regions are states (`california`, `texas`). For France, Italy, and similarly sized countries, they are editorial or administrative groupings (`south`, `tuscany`). The word "region" is used for all of them regardless of their political status.

What a region page looks like:
- Overview describing the area and what makes it worth visiting as a whole
- Its own POIs for things that belong to the region but not to any specific city (a viewpoint on a mountain pass, a monument between towns)
- Child cities and features visible in the sidebar

What a region page does **not** have:
- `eating_out`, `bars_and_cafes`, or `shopping` sections — those belong on city pages
- Child regions — there is no third level. A region cannot contain another region.

## Features and city–feature links

A feature is a named area worth visiting that is not itself a settlement: Cinque Terre, the Ardèche gorge, Normandy, Côte d'Azur, Loire Valley, Big Sur, Yellowstone. Features sit inside their parent region alongside cities.

**Features can have their own POIs** — the hiking trailhead, the viewpoint, the specific beach, the small village too tiny for its own city page.

**Cities link to features via `tags`**. A city that is closely associated with a feature adds the feature's slug to its tags list:

```yaml
# content/europe/italy/liguria/riomaggiore.md
title: Riomaggiore
type: location
loc_type: city
tags:
  - cinque_terre
```

This is the same tag mechanism used for neighbourhood and section membership. The feature page can then surface its tagged cities. A city may tag into more than one feature if it genuinely sits within both.

The distinction between a feature and a city:
- **Feature**: you go *to* the area (Cinque Terre, Ardeche, Loire Valley, Normandy). The area is the draw; cities within it are the places you sleep.
- **City**: you go *to* the place itself. It stands alone as a destination.

Some places work as both — Avignon is a city but could also tag into Provence. Use judgement: if the place has a mayor and a post office, it's a city; if it's primarily a landscape or named area, it's a feature.

## The overview page

The overview is the most important page. It should make someone want to visit — or at least understand the place. See STYLE.md for detailed guidance, but in short:

1. Open with what makes this place distinctive
2. Paint the picture — walk through the neighbourhoods, the highlights, the character
3. Be practical and opinionated — if something is great, say it's great
4. 3–5 paragraphs for a city, shorter for a small town

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
