# Curbside POIs Task

Add curbside POIs to a city — the kind of things a walking tour guide would stop at and explain. These are not tourist attractions or restaurants; they are named houses, public art, memorials, historic buildings, interesting street names, churches, and city infrastructure with a story.

Curbside POIs appear on the explore map only at zoom ≥15 as small dots. They are invisible in the regular guide (no section page exists for `curbside`). They require a fun fact or specific story — if you cannot find one, skip the item.

## Format

```yaml
---
title: "Name of the thing"
type: poi
latitude: 52.12345
longitude: 5.12345
snippet: "One line describing what it is and why it's interesting"
tags: [curbside]
score: 1
---
```

Body: 2–3 short paragraphs. Lead with the story or the surprising fact. Explain the WHY — why is the name what it is, what happened here, what does this building tell you about the city. Do not write "this is a ..." descriptions that repeat the snippet; add the layer underneath it.

## What to include

The test: **would a knowledgeable walking tour guide stop here and say something interesting?**

Good candidates:
- **Public art and sculptures** with a known title, artist, or story
- **Memorials and plaques** — WWII, famous residents, historical events
- **Named historic buildings** — former inns, guild houses, almshouses (hofjes), toll houses, watch posts
- **Medieval infrastructure** — towers, gates, sluices, city walls, bridges with names
- **Interesting street names** — names that encode history: former canals, trades, animals kept there, events
- **Historic places of worship** — churches, cathedrals, chapels, synagogues, with a specific story
- **Neighbourhood nicknames** with a known origin story

Skip:
- Items with no discoverable story or fun fact
- Modern generic public art with no narrative
- Active businesses or restaurants (even in historic buildings)
- Anything already covered as a regular POI in the city's guide

## Workflow

### 1. Find candidates via Overpass — start here, not from memory

**The coordinates must come from OSM, not from model memory.** The correct approach is to query Overpass first, get the real list of named things with their exact GPS coordinates, and then write content only for what actually exists. Never invent a list of places and then try to find coordinates — do it in the other direction.

Use the script `tools/fetch_barcelona_osm.py` as a template. Adapt it for the target city's bounding box. The script queries Overpass and outputs a JSON file of candidates with exact OSM coordinates.

Run one combined query to get artworks, memorials, historic nodes, named buildings, churches, and fountains:

```
[out:json][timeout:120];
(
  node["tourism"="artwork"]["name"](<bbox>);
  way["tourism"="artwork"]["name"](<bbox>);
  node["historic"]["name"](<bbox>);
  way["historic"]["name"](<bbox>);
  node["memorial"]["name"](<bbox>);
  way["memorial"]["name"](<bbox>);
  node["amenity"="fountain"]["name"](<bbox>);
  way["amenity"="fountain"]["name"](<bbox>);
  node["tourism"="attraction"]["name"](<bbox>);
  way["tourism"="attraction"]["name"](<bbox>);
  node["amenity"="place_of_worship"]["name"]["wikipedia"](<bbox>);
  way["amenity"="place_of_worship"]["name"]["wikipedia"](<bbox>);
  node["amenity"="place_of_worship"]["name"]["wikidata"](<bbox>);
  way["amenity"="place_of_worship"]["name"]["wikidata"](<bbox>);
  node["building"="church"]["name"](<bbox>);
  way["building"="church"]["name"](<bbox>);
  node["building"="cathedral"]["name"](<bbox>);
  way["building"="cathedral"]["name"](<bbox>);
  way["building"]["name"]["wikipedia"](<bbox>);
  way["building"]["name"]["wikidata"](<bbox>);
);
out center;
```

Replace `<bbox>` with `<south>,<west>,<north>,<east>`.

For cities with a medieval old town, also query streets whose names record their original function. The pattern is universal: any city old enough will have streets named after the trade, material, or activity once there — tanners, blacksmiths, chandlers, a former canal, a demolished gate. Restrict the bounding box to the old centre, not the whole city.

```
[out:json];
way["highway"]["name"](<old-city-bbox>);
out center body;
```

Filter the results manually — look for names that encode a former role: trades (Argenters = silversmiths, Ferrers = blacksmiths), materials (Blanqueria = tanning, Corders = rope), infrastructure (Portaferrissa = iron gate, Boqueria = stalls), natural features (Rambla = dry riverbed). Skip generic names and modern streets. Keep only those where you can write a sentence explaining what happened there.

### 2. Filter candidates

Remove:
- Items already in the guide as regular POIs (check `content/<city-path>/`)
- Items with no story you can write (no name, no history, no interesting tag values)
- Duplicates (same location, two OSM elements)

Quality signal: prefer items with `wikipedia` or `wikidata` tags — these are more likely to have a notable story. Items without either can still be included if the OSM tags suggest something interesting (e.g. `historic=castle`, `artwork_type=sculpture`).

### 3. Audit existing POIs for coordinate accuracy

Before creating new stubs, cross-reference the Overpass results against existing (non-curbside) POIs already in the city's content directory. This is a free quality pass: you already have the authoritative OSM coordinates in the candidates JSON.

For each existing POI file in `content/<city-path>/` that has `type: poi` and is **not** tagged `curbside`:

1. Normalise its title to a slug and look for a matching entry in the candidates JSON (match on `slug` or fuzzy-match on `name`).
2. If a match is found, compare the stored `latitude`/`longitude` against the OSM values.
3. If they differ by more than roughly 100 m (≈0.001° in either axis), update the file's coordinates to the OSM values using `python-frontmatter`. Log what changed.

```python
import frontmatter, os, json, math

def dist(lat1, lon1, lat2, lon2):
    return math.hypot(lat1 - lat2, lon1 - lon2)

with open('candidates.json') as f:
    candidates = {c['slug']: c for c in json.load(f)}

city_dir = 'content/europe/spain/catalonia/barcelona'
for fname in os.listdir(city_dir):
    if not fname.endswith('.md'):
        continue
    path = os.path.join(city_dir, fname)
    post = frontmatter.load(path)
    if post.get('type') != 'poi' or 'curbside' in post.get('tags', []):
        continue
    slug = fname[:-3]
    if slug not in candidates:
        continue
    c = candidates[slug]
    stored_lat = post.get('latitude')
    stored_lon = post.get('longitude')
    if stored_lat is None or stored_lon is None:
        continue
    if dist(stored_lat, stored_lon, c['lat'], c['lon']) > 0.001:
        print(f"Fix {slug}: ({stored_lat}, {stored_lon}) → ({c['lat']}, {c['lon']})")
        post['latitude'] = c['lat']
        post['longitude'] = c['lon']
        with open(path, 'wb') as out:
            frontmatter.dump(post, out)
```

Only fix coordinates where the OSM match is clearly the same place. If the name is common or ambiguous, skip rather than guess.

### 4. Create stub files from Overpass data

Use `tools/create_curbside_stubs.py` (adapt the path and candidates JSON for your city) to write all stub files with frontmatter in one step. The script writes exact OSM coordinates to every file. **Do not change the coordinates after this step.**

```python
# Stub format — written by the script, not manually:
---
title: "Name from OSM"
type: poi
latitude: 41.38547  # exact from Overpass
longitude: 2.17832  # exact from Overpass
tags: [curbside]
score: 1
---
```

### 5. Write content (snippet + body)

For each stub, add:
- `snippet:` field in frontmatter — one sentence: what it is and why interesting
- Body: 2–3 paragraphs

**Do not change latitude or longitude.** They came from OSM and are correct.

Commit each logical batch together. Group by neighbourhood or type (artworks, churches, memorials, etc.).

### 6. What makes a good body text

- Lead with the surprising or non-obvious fact
- Explain the name etymology if it encodes history
- Give the historical context that makes the object meaningful
- End with something about what it's like to stand there, if relevant
- No need to describe what the object looks like — people can see it

### Examples of good curbside POIs

- A medieval tower named "Dieventoren" (Thieves' Tower) — write about what it was used for
- A street named "Havik" (Hawk) — write about the falconry that happened there
- A 17th-century logement named after a gaping face sign — explain the gaaper tradition
- A Yugoslav partner-city stone — write about the country that no longer exists
- A street named "Blekerseiland" — explain the textile bleaching process

### Examples of what to skip

- A fountain named "Fontein" with no other information
- A sculpture called "Untitled"
- A modern shopping-street artwork placed in 2019 with no context
- A church that is already a regular POI in the guide

## Branch naming

Follow the standard curbside branch convention: `curbside/<city-slug>`, e.g. `curbside/amersfoort`, `curbside/barcelona`.
