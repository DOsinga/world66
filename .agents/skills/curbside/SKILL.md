---
name: curbside
description: build the curbside explore map for a city — query OSM for interesting places, create POI stubs with locked coordinates, write content via agents. Invoke when the user wants to add curbside POIs for a city.
argument-hint: <content-path, e.g. europe/spain/catalonia/barcelona>
---

Build the curbside explore-map layer for a World66 city. Curbside POIs appear as map dots at zoom ≥15 and may also appear in section pages (sightseeing, eating_out, nightlife) if they have the relevant tag.

## What is a curbside POI?

```yaml
type: poi
tags: [curbside]        # add section tags (sightseeing, eating_out, nightlife) for major places
score: 1
latitude: 41.3862153   # always from OSM — never invent or round aggressively
longitude: 2.1699987
snippet: One-sentence hook for the map tooltip.
```

## OSM-first rule

**All candidates must come from OpenStreetMap.** Never invent a place from training knowledge. The workflow is:
1. Query Overpass → get named items with GPS coordinates
2. Check candidates against existing files (avoid dupes)
3. Present filtered list to user for review
4. Create stubs with OSM coordinates locked in
5. Write content via agents

## Overpass query pattern

```
[out:json][timeout:60];
(
  node["key"="value"](LAT_S,LON_W,LAT_N,LON_E);
  way["key"="value"](LAT_S,LON_W,LAT_N,LON_E);
  relation["key"="value"](LAT_S,LON_W,LAT_N,LON_E);
);
out center tags;
```

Use `out center tags;` for ways/relations to get a centre point. For named POIs without explicit lat/lon (ways, relations), use the `center` object from the response.

Useful OSM tag queries for curbside content:
- `highway=pedestrian + name=*` — pedestrian squares and major streets
- `place=square + name=*` — named squares
- `historic=memorial + name=*` — memorials and plaques
- `historic=monument + name=*` — monuments  
- `historic=building + name=*` — named historic buildings
- `amenity=theatre + name=*` — theatres
- `amenity=cinema + name=*` — cinemas
- `amenity=marketplace + name=*` — markets
- `tourism=museum + name=*` — museums
- `tourism=attraction + name=*` — major attractions
- `amenity=restaurant + name=* + wikipedia=*` — famous restaurants (filter by wikipedia link)
- `amenity=bar + name=* + wikipedia=*` — famous bars
- `leisure=park + name=*` — parks
- `man_made=bridge + name=*` — named bridges
- `historic=stolperstein + name=*` — Stolpersteine (memorial pavement stones)

Bounding box for Overpass: use the city's approximate bbox. Expand per neighbourhood as needed.

## Finding the bbox

Read the city's main `.md` file for `latitude` and `longitude`, then add ~0.05° in each direction for a small city, ~0.1° for a large one. Alternatively, fetch the city's OSM relation extent.

## Slug and stub creation

```python
import os, re, frontmatter

def slugify(name):
    name = name.lower()
    for a, b in [('à','a'),('á','a'),('â','a'),('ä','a'),('è','e'),('é','e'),('ê','e'),('ë','e'),
                 ('ì','i'),('í','i'),('î','i'),('ï','i'),('ò','o'),('ó','o'),('ô','o'),('ö','o'),
                 ('ù','u'),('ú','u'),('û','u'),('ü','u'),('ñ','n'),('ç','c'),('·','')]:
        name = name.replace(a, b)
    name = re.sub(r'[^a-z0-9]+', '_', name)
    return name.strip('_')[:60]

def create_stub(title, lat, lon, path):
    post = frontmatter.Post('', title=title, type='poi',
        latitude=round(lat, 7), longitude=round(lon, 7),
        tags=['curbside'], score=1)
    with open(path, 'wb') as f:
        frontmatter.dump(post, f)
```

Check against `os.listdir(city_dir)` before creating to avoid dupes. Also check for existing files with similar names (normalization: strip articles like "la", "el", "les", "the", lower-case, strip diacritics).

## Writing content

Each curbside POI needs:
- `snippet:` in frontmatter — one sentence, the non-obvious hook for the map tooltip
- Body: 2-3 paragraphs, World66 voice (authoritative, specific, no fluff)
- Lead with the non-obvious fact — what a guidebook wouldn't say first
- Do NOT change `latitude` or `longitude`

Delegate writing to parallel agents in batches of 5-10. Brief each agent with the facts it needs — don't make agents do their own research.

## Categories and section-tag upgrades

Not all curbside POIs need section tags. Apply them when the place is significant enough to appear in a section page:

| Place type | Section tag |
|-----------|------------|
| Major museum, landmark, historic site | `sightseeing` |
| Famous restaurant, market, café | `eating_out` |
| Theatre, concert venue, cinema, bar | `nightlife` |

A minor street plaque or stolperstein stays `curbside`-only. A major market gets `[curbside, eating_out]`.

## Dupe check (important)

After running multiple OSM queries, the city directory may grow to include duplicates from the original World66 crawl. Before finalising:

1. Normalize all titles (lower, strip articles, strip diacritics)
2. Flag pairs with identical normalized titles
3. For each pair: if one file has proper section tags and a higher score, it's from the original crawl — keep it, add `curbside`, delete the new stub
4. If both are curbside-only, keep the better-named file and merge content if needed

## Workflow summary

1. **Query OSM** via Overpass for multiple categories
2. **Filter**: remove already-covered slugs, transit infrastructure, generic chain stores
3. **Present** filtered candidates to user, grouped by category
4. **User selects** which to add
5. **Create stubs** with locked OSM coords
6. **Write content** via parallel agents (5-10 per batch)
7. **Lint** (`python3 tools/linter.py --fix`)
8. **Commit** each batch separately
9. **Dupe check** when the set is large
10. **Upgrade section tags** on places significant enough to appear in sections
11. **Push** and open PR when the city feels complete

## Branch naming

Use `curbside/<city>` (e.g. `curbside/barcelona`, `curbside/marseille`). Push to that branch throughout; open one PR per city when done.
