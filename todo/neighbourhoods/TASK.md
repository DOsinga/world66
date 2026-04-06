# Neighbourhoods Task

Add a rich `explore` section to major cities — a guide to the city's distinct neighbourhoods and areas, each with a proper intro, a hero image, and cross-references to the POIs already listed in other sections.

This task is for **major cities only**. Each batch contains exactly one city.

## Before you start — checks

Run these checks on the city before doing any writing. Fix problems first, then proceed.

### 1. Location cleanup done?

Check the city's main `.md` file for `done: location_cleanup`. If it's missing, run the location_cleanup task first or skip this city and pick another batch.

### 2. Enough POIs?

Count POIs across `things_to_do/`, `eating_out/`, and `bars_and_cafes/`. A city needs **at least 15 POIs total** to support meaningful neighbourhood tagging. If it's thin:

- Check if the POI directories exist at all — if not, the cleanup wasn't done properly, skip it.
- If there are 8–14 POIs, proceed but only tag what exists; note the gap in the commit message.
- If there are fewer than 8, skip this city.

### 3. Coordinate sanity check

For every POI that has `latitude` and `longitude`, verify the coordinates are plausible for this city. A quick rule: look up the city's approximate bounding box and flag any POI whose coordinates fall outside it. Common failures:

- Coordinates of `0, 0` — missing data pasted as null
- Coordinates in a completely different country (e.g., a Paris POI with New York coordinates)
- Coordinates that look swapped (lat/lng reversed)

Fix bad coordinates before tagging POIs to neighbourhoods — a POI with wrong coordinates on a neighbourhood map is worse than no POI.

To fix: look up the correct coordinates for the place (use web search), update the file, note the fix in the commit message.

### 4. Section structure correct?

Confirm the city uses `things_to_do/` (not `sights/` or `museums/`), and that `bars_and_cafes/` exists if relevant. If old section names are still present, do a quick structural fix first (or note it and skip tagging those POIs).

## What to build

For each city, create:

1. **`explore.md`** — the section file
2. **`explore/neighbourhood_slug.md`** — one file per neighbourhood (15–25 for a world capital, 8–15 for a smaller major city)

### Section file (`explore.md`)

```yaml
---
title: "Explore by Neighbourhood"
type: section
---

Brief intro (2–3 sentences) describing how the city divides into areas and why it's worth exploring neighbourhood by neighbourhood.
```

### Neighbourhood file (`explore/soho.md`)

```yaml
---
title: "Soho"
type: neighbourhood
latitude: 51.5137
longitude: -0.1337
image: soho.jpg
image_source: "https://commons.wikimedia.org/wiki/File:..."
image_license: "CC BY-SA 4.0"
---

[3–5 paragraphs about the neighbourhood: its character, history, what it looks like, what draws people there, what time of day is best, what makes it different from adjacent areas.]
```

The `type: neighbourhood` distinguishes these from regular sections and locations.

### Neighbourhood writing guide

- **Specific and vivid.** Name streets, squares, markets, buildings. Not "there are many cafes" but "the cafes along Exmouth Market spill onto the pavement".
- **Character over logistics.** What does it feel like? What kind of people live there? What's the history?
- **Honest about rougher edges.** If part of an area is under construction or touristed to death, say so.
- **3–5 paragraphs minimum** for major neighbourhoods. Smaller satellite areas can be shorter.
- **Research using web search** — do not invent details, street names, or history.

### Images

Find a freely licensed image (Wikimedia Commons preferred) for each neighbourhood. Every neighbourhood file should have `image`, `image_source`, and `image_license`.

### Tagging POIs

After creating the neighbourhood files, go through the city's existing sections (`things_to_do/`, `eating_out/`, `bars_and_cafes/`, etc.) and add `neighbourhood: "Exact Title"` to any POI that belongs to a neighbourhood. The title must match the neighbourhood file's `title:` exactly (case-sensitive).

This makes the POI show up on the neighbourhood page automatically without removing it from its section.

## What makes a good neighbourhood list

Cover the full city — don't only do the tourist centre. Include:

- The historic core and main tourist areas
- Up-and-coming and creative quarters
- Traditional working-class areas
- Waterfront or riverside areas where they exist
- University districts
- Ethnic enclaves and market areas
- The "locals go here" neighbourhoods

For London: aim for 20+. For cities like Krakow or Amman: 8–12 is fine.

## Commit format

```
Neighbourhoods: City Name
```

One commit per city (the whole batch is one city).

## Done stamp

Add to the city's main `.md` file:

```yaml
done:
  neighbourhoods: <today's date>
```

(alongside any existing `done:` entries)

## Commit message format

```
Neighbourhoods: City Name

- N neighbourhoods created
- M POIs tagged across things_to_do/, eating_out/, bars_and_cafes/
- X bad coordinates fixed (list them)
- any other notable issues
```
