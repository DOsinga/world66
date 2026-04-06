# Neighbourhoods Task

Add a rich `explore` section to major cities — a guide to the city's distinct neighbourhoods and areas, each with a proper intro, a hero image, and cross-references to the POIs already listed in other sections.

This task is for **major cities only**. Each batch contains exactly one city.

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
  neighbourhoods: 2026-04-06
```

(alongside any existing `done:` entries)
