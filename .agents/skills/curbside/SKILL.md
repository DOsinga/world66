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
3. Create stubs with OSM coordinates locked in
4. Write content via agents

## Scope: be broad, not curated

**All named buildings are candidates.** A named church, hospital, school, factory, old palace, office tower — any of these can have a story. Don't pre-filter based on assumed tourist interest. Filter only the obviously useless:

- No name at all
- Pure residential apartment blocks (`building=apartments`, `building=residential`)
- Single-letter or pure-number names (OSM tagging artifacts)
- National chain stores (Carrefour, McDonald's, H&M, etc.)

A major city should produce **300–700 curbside stubs**. Err on the side of more — it is easy to delete stubs that turn out to be uninteresting, harder to notice what you missed.

## Overpass query pattern

```python
import urllib.request, urllib.parse, json

def overpass(query):
    url = 'https://overpass-api.de/api/interpreter'
    data = urllib.parse.urlencode({'data': query}).encode()
    headers = {'User-Agent': 'World66/1.0 (travel guide research)', 'Accept': '*/*'}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())
```

Always include the `User-Agent` header — bare requests get HTTP 406. Use `out center tags;` so ways and relations return a centre point.

Run multiple queries by category:
- `place=square + name=*` — named squares
- `highway=pedestrian + name=*` — pedestrian streets and areas
- `historic=* + name=*` — all historic items (memorial, monument, building, castle, fort…)
- `tourism=* + name=*` — museums, attractions, artworks
- `amenity=theatre + name=*`, `amenity=cinema + name=*`, `amenity=marketplace + name=*`
- `leisure=park + name=*` — parks and gardens
- `amenity=place_of_worship + name=* + wikipedia=*` — religious buildings with Wikipedia
- `amenity=restaurant + name=* + wikipedia=*`, `amenity=bar + name=* + wikipedia=*`
- `building=* + name=*` — all named buildings in the city centre bbox

## Bounding box

Read the city's `.md` file for `latitude` and `longitude`. Add ±0.08–0.12° for a large city. Use a tighter inner-city bbox for the named-buildings query to avoid sprawling suburbs.

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

Dedup by slug against `os.listdir(city_dir)`. Skip slugs that already exist as files.

## Writing content

Each curbside POI needs:
- `snippet:` in frontmatter — one sentence, the non-obvious hook for the map tooltip
- Body: 2-3 paragraphs, World66 voice (authoritative, specific, no fluff)
- Lead with the non-obvious fact — what a guidebook wouldn't say first
- **Never change `latitude` or `longitude`**

Delegate writing to parallel agents in batches of 5-10. Brief each agent with the key facts — the agent should not need to do its own research. Pull facts from the OSM data you already fetched, Wikipedia summaries you've read, or direct knowledge.

## Section-tag upgrades

After creating stubs, upgrade significant places to also appear in section pages. Keep `curbside` and add:

| Place type | Add tag |
|-----------|---------|
| Major museum, landmark, historic site, square | `sightseeing` |
| Famous restaurant, market, food hall | `eating_out` |
| Theatre, concert venue, cinema, bar, nightclub | `nightlife` |

A small wall plaque stays `curbside`-only. A major covered market gets `[curbside, eating_out]`.

## Dupe check

After running multiple OSM queries, cross-check against the original World66 crawl files already in the city directory. Normalize titles (lower, strip articles, strip diacritics) and flag slug-collision pairs. For each dupe:
- If the old file has proper section tags and a higher score → it's from the original crawl; add `curbside` to it and delete the new stub
- If both are curbside-only → keep the better-named one

## Workflow summary

1. **Query OSM** via Overpass across all categories
2. **Combine and dedup** by slug; save raw JSON for later cross-referencing
3. **Filter** only obvious junk (apartments, chains, single-letter names)
4. **Create stubs** for everything else with locked OSM coordinates
5. **Write content** via parallel agents in batches
6. **Lint** (`python3 tools/linter.py --fix`)
7. **Commit** each batch; push to `curbside/<city>` throughout
8. **Dupe check** — merge old crawl entries with `curbside` tag, delete new duplicates
9. **Upgrade section tags** on the most significant places
10. **Open PR** when the city feels complete

## Branch naming

Use `curbside/<city>` (e.g. `curbside/barcelona`, `curbside/marseille`). One PR per city.
