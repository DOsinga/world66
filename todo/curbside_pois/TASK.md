# Curbside POIs Task

Add curbside POIs to a city — the kind of things a walking tour guide would stop at and explain. These are not tourist attractions or restaurants; they are named houses, public art, memorials, historic buildings, interesting street names, and city infrastructure with a story.

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
score: 0
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
- **Historic places of worship** with a specific story (synagogues, unusual churches, plague chapels)
- **Neighbourhood nicknames** with a known origin story

Skip:
- Items with no discoverable story or fun fact
- Modern generic public art with no narrative
- Active businesses or restaurants (even in historic buildings)
- Anything already covered as a regular POI in the city's guide

## Workflow

### 1. Find candidates via Overpass

Run one combined query to get artworks, memorials, historic nodes, and named buildings:

```
[out:json];
(
  node["tourism"="artwork"]["name"](<bbox>);
  way["tourism"="artwork"]["name"](<bbox>);
  node["historic"]["name"](<bbox>);
  way["historic"]["name"](<bbox>);
  node["amenity"="fountain"]["name"](<bbox>);
  way["building"="house"]["name"](<bbox>);
  way["building"]["name"]["historic"](<bbox>);
);
out center body;
```

Replace `<bbox>` with `<south>,<west>,<north>,<east>` — a bounding box covering the city centre and inner neighbourhoods, typically about 0.04° × 0.06°.

Also query for interesting street names — nodes/ways with `highway` and evocative names:

```
[out:json];
way["highway"]["name"~"<pattern>"](<bbox>);
out center body;
```

Useful Dutch patterns: `[Ss]teeg` (alley), `[Gg]racht` (canal), `[Hh]aven` (harbour), `[Mm]olen` (mill), `[Pp]oort` (gate), `[Hh]of` (courtyard). Adapt for the city's language.

### 2. Filter

Remove:
- Items already in the guide as regular POIs (check `content/<city-path>/`)
- Items with no story you can write (no name, no history, no interesting tag values)
- Duplicates (same location, two OSM elements)

### 3. Get coordinates from Nominatim

For each item, confirm coordinates via Nominatim rather than trusting the raw Overpass centroid, especially for building ways:

```
https://nominatim.openstreetmap.org/search?q=<name>+<city>&format=json&limit=2
```

Use `User-Agent: world66-content/1.0`.

### 4. Write POI files

One file per item at `content/<city-path>/<slug>.md`. Slugs: lowercase, underscores, no special characters.

Commit each batch together with a descriptive message. Group logically (all artworks, all Keien, all historic buildings, etc.).

### 5. What makes a good body text

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
