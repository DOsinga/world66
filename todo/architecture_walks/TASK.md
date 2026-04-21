# Architecture Walks Task

Create a guided walking route organised around what buildings look like and why they look that way. The walk teaches visual literacy: how to read a façade, identify a period, understand why a city looks the way it does. Each stop is a building or group of buildings that illustrates something about how and why the city was built. The result should feel like being shown around by a knowledgeable architect or architectural historian — someone who can make you see the ordinary streetscape differently.

See the Jordaan Walk (`content/europe/netherlands/amsterdam/jordaan_walk.md`) as the reference for file structure and routing. The difference is in how stops are selected and written.

## File structure

```
content/<city-path>/
  city_walks.md              # section page (create if missing)
  <walk_slug>.md             # the walk itself (type: walk)
  <waypoint_slug>.md         # one file per new waypoint POI
```

## Step 1 — Active research: find buildings of architectural interest

Do not rely on general knowledge. Run the searches below before selecting any stops. The goal is to surface buildings and streets you would not have thought of, and to find the specific details (architects, dates, building names, street addresses) that make each stop worth writing about.

### 1a — Neighbourhood architecture searches

Run all of the following searches and read the results:

```
"[neighbourhood] [city] architecture"
"[neighbourhood] [city] architectural history"
"[neighbourhood] [city] notable buildings"
"[neighbourhood] [city] listed buildings" OR "rijksmonument [neighbourhood]" (Netherlands)
"[neighbourhood] [city] architecture guide"
"[architect name] [neighbourhood]" — for any architects associated with the area
```

For Dutch cities, also search:
```
"[neighbourhood] Amsterdam School" OR "Amsterdamse School [neighbourhood]"
"[neighbourhood] grachtenpanden" OR "[neighbourhood] gevelstenen"
"rijksmonumenten [neighbourhood] [city]"
```

Read at least 4–5 distinct sources. Wikipedia is a starting point, not an ending point.

### 1b — Query the heritage register

For the Netherlands, the Rijksdienst voor het Cultureel Erfgoed maintains a register of protected monuments. Search:
```
site:monumenten.nl "[neighbourhood]"
"rijksmonument [street name]"
```

For other countries, find the equivalent national or municipal listed buildings register and search it. Heritage annotations explain *why* a building is significant — this is often the most useful source for architectural details.

### 1c — Find the architectural styles present in the area

Search for each style that may be present in the area:
```
"[style name] [city] examples"
"[style name] [neighbourhood]"
```

For Amsterdam: search separately for Golden Age canal houses, Amsterdam School, Jugendstil/Art Nouveau, Berlage, Functionalism/Het Nieuwe Bouwen, post-war reconstruction. Each style has a different geographic concentration.

### 1d — Find specific streets and buildings

For each promising street or building you encounter in your research:
```
"[street name] [city] architecture"
"[building name] [city] architect"
"[building name] [city] bouwjaar" (year built, for Dutch sources)
```

Look for: the architect's name, the year of construction, the client or commissioner, any specific detail the building is known for (a particular gable stone, a mosaic, a structural innovation).

### 1e — Compile a sourced candidate list

Before selecting stops, write out a candidate list of **at least 10 buildings or locations**, each with:
- Address or description
- What makes it architecturally significant
- Source (where you found this information)
- Any specific detail you verified

Do not proceed to Step 2 until you have this list. Buildings you know from general knowledge are allowed on the candidate list only if you have verified the key facts (architect, date, specific detail) against a source found in Steps 1a–1d.

**The test for a good stop**: can you point at something on the building and explain exactly what it tells you? A gable type, a cornice detail, a brick pattern, a window proportion — something you can see from the pavement. If the stop requires background knowledge but produces nothing visible on the spot, find a better stop.

Discard candidates that are similar to each other — you don't need three examples of the same gable type. Prioritise variety in period, variety in building type, and variety in scale.

## Step 2 — Build the walk around the architecture

Once you have the buildings, map the locations. A good architecture walk:
- Covers 1–3 km (people stop and look; they don't sprint)
- Spans at least two distinct periods or styles — ideally three or more
- Includes at least one stop where the contrast with an adjacent building is part of the point
- Has at least one stop where you teach the reader a term or concept they will use for the rest of the walk (and can then apply in other cities)
- Includes variety in building type: not five houses in a row, but houses and a church and a civic building and something industrial

The walk should have a **loose argument** — not just a tour of interesting buildings, but a claim about what the city looks like and why. Examples:
- This neighbourhood was built in one decade by one developer and looks like it
- You can read 400 years of the city's self-image in these three blocks
- Every building here is trying to do the same thing in a different way
- The rich lived on one side of this canal; this is what that looked like

## Step 3 — Research each selected stop thoroughly

For each building on your shortlist, run dedicated searches before writing anything:

```
"[building name or address] [city] architect"
"[building name or address] [city] history"
"[architect name] [city]" — to understand the architect's broader body of work
```

For each stop you need to establish, from a source:
- **The style and period**: when was it built, in what style, and what does that mean visually?
- **The architect** (if known): who were they, what else did they build, what were they reacting against?
- **The commission**: who paid for it and why? What were they trying to say?
- **The specific visible detail**: what can you point at from the pavement — the thing that makes this building readable once you know what to look for
- **The context**: what was there before, what came after, what is it next to?

Architectural history is full of misattributions and oversimplifications. Cross-reference anything that seems uncertain. If you cannot verify a claim about an architect or date, do not include it — write around the uncertainty rather than inventing confidence.

The POI description (2–4 sentences in the waypoint file) names the style and identifies the visible detail. The walk prose is where you explain what it means.

## Step 4 — Pick waypoints and get coordinates

For each stop, check whether a POI file already exists in the city's sections. If so, reference it as `things_to_do/slug` in the `waypoints:` list. If not, create a new POI file at the city root.

### Getting waypoint coordinates from OSM

Use the Nominatim API to find coordinates for named places:

```
https://nominatim.openstreetmap.org/search?q=PLACE+NAME+CITY&format=json&limit=1&accept-language=en
```

For specific buildings or building groups at an address, use the Overpass API:

```
https://overpass-api.de/api/interpreter?data=[out:json];node["name"="EXACT NAME"](LAT_MIN,LNG_MIN,LAT_MAX,LNG_MAX);out;
```

Add 1–2 seconds of delay between requests to avoid rate limiting.

Each waypoint POI file needs `latitude` and `longitude`. Without them the marker won't appear on the map.

**Critical: Nominatim returns area centroids, not street points.** A coordinate returned for a POI "on" a street may be 50–100m from the actual street. This causes routing to silently follow a parallel street. For any waypoint that needs to be at a precise street location:

1. Query the **street itself** via Nominatim to get its actual lat/lng:
   ```
   https://nominatim.openstreetmap.org/search?q=STREET+NAME+CITY&format=json&limit=5&accept-language=en
   ```
2. After routing, verify with OSRM step names (`&steps=true`) that each segment is on the correct street.

## Step 5 — Get the walking route

The `route:` field traces the actual walking path. See the [city_walks TASK.md](../city_walks/TASK.md) for the complete technical instructions on using OSRM, forcing waypoints along streets, avoiding backtracking, and sanity-checking the route. All of those apply here.

The short version:
- Use `routing.openstreetmap.de/routed-foot`, not `router.project-osrm.org`
- Use `&steps=true` to verify street names in the route
- Add forcing waypoints (not named stops) to keep the route on specific streets
- Split into segments and stitch if needed to avoid U-turns

## Step 6 — Write the walk

### The walk file (`<slug>.md`)

```yaml
---
title: "The [Area] Architecture Walk"
type: walk
tags:
  - city_walks
latitude: <start lat>
longitude: <start lng>
waypoints:
  - things_to_do/existing_poi
  - new_waypoint_slug
route:
  - [52.123456, 4.123456]
  - ...
---
```

### Prose style

Write like an architectural historian who enjoys being understood. Not a textbook. Not a glossary. Someone who can explain what a pilaster is by pointing at one and saying "that column that's not actually a column — that's a pilaster, and it's doing this job."

**The opening** names the walk's argument: what will the reader understand about this city's built environment by the end? Drop them into the visual world immediately — describe what they are looking at before explaining what it means.

**At each stop**, the structure is roughly:
1. Orient them: what building are they looking at? What is its address, what does it look like at a glance?
2. Name it: what style, what period, what type of building?
3. Teach them to read it: point at the specific visible detail — gable type, window proportions, brick colour, ornamental programme — and explain what it means
4. Context: why was it built this way? What was the architect or client trying to do?
5. What it tells you more broadly: what does this building say about the city, the period, or the people who built it?

Not every stop needs all five. Some buildings are best understood through contrast with what's next to them. But every stop needs **the visible detail** — the thing you can point at.

**Transitions between stops** are not dead space. Use them to describe what you pass along the way: the ordinary streetscape, the backdrop architecture, the things that are typical rather than exceptional. An architecture walk should make the whole street readable, not just the highlighted buildings.

**Introduce vocabulary early** and use it consistently. If you explain what a neck gable is at stop 2, you can refer to neck gables at stop 5 without re-explaining. Build the reader's vocabulary as the walk progresses.

**The close** should name what the reader now knows that they didn't at the start — the lens through which they will see other streets in this city.

**End with distance and time**: "The walk is approximately X km and takes about Y minutes at a comfortable pace."

### Tone

- Specific terms are better than vague descriptions: "a neck gable with flanking volutes" beats "an ornate top to the building"
- But always explain the term on first use: never drop jargon without unpacking it
- Name architects and dates: "Hendrick de Keyser, 1620" is more useful than "a 17th-century architect"
- Comparisons help: "the proportions are wider and squatter than the Golden Age houses to the north — this is what 1870s speculative development looks like"
- Don't over-praise: "magnificent," "stunning," "breathtaking" — let the reader decide. Describe what makes the building work.

### Waypoint POI files

For new waypoints, create a file at the city root:

```yaml
---
title: "Bloemgracht 87–91"
type: poi
latitude: 52.3743
longitude: 4.8797
---

Three stepped-gable houses built in 1642, considered the finest surviving example of Golden Age Jordaan domestic architecture. Each gable carries a carved stone identifying the owner's trade: townsman, farmer, sailor. The stepped gable — each face of the step a separate right angle — is the earliest and most common Golden Age type; by 1660 it had been largely superseded by the neck gable.
```

The POI body names the style, identifies the visible detail, and gives one piece of broader context. 2–4 sentences.

**Do not add `tags: - city_walks` to waypoint POI files.** That tag makes them appear as items in the city_walks section listing alongside the walks themselves. Waypoint POIs are reached via the walk's waypoints list, not by browsing the section. Only the walk file itself should carry `tags: - city_walks`.

## Step 7 — Create the section file (if missing)

If `city_walks.md` doesn't exist in the city root:

```yaml
---
title: "City Walks"
type: section
---

Guided walks through [city]'s most distinctive neighbourhoods, with routes, waypoints, and things to look out for along the way.
```

## Step 8 — Commit

```
Architecture walk: [City] — [Walk Name]

- X waypoints, Y km
- N new waypoint POIs created
- Period range: [earliest] to [latest]
```

One commit per walk.

## Quality checklist

- [ ] At least 4 distinct web sources were consulted during Step 1 research
- [ ] A sourced candidate list of 10+ buildings was compiled before selecting stops
- [ ] Every stop's architect, date, and key detail has been verified against a source found during research (not assumed from general knowledge)
- [ ] Each stop has at least one specific visible detail the reader can identify on the spot
- [ ] The walk introduces at least one architectural term and uses it consistently
- [ ] The opening names the walk's argument
- [ ] The close names what the reader now knows
- [ ] Variety in period and building type across stops
- [ ] At least one stop uses contrast with an adjacent building
- [ ] All waypoints have `latitude` and `longitude`
- [ ] Route coordinates are `[lat, lng]` (not `[lng, lat]`)
- [ ] Route starts near waypoint 1 and ends near the last waypoint
- [ ] OSRM step names verified — route follows the intended streets
- [ ] All links in the prose point to real pages
- [ ] Walk body ends with distance and time estimate
- [ ] `city_walks.md` section exists in the city root
- [ ] No `tags: - city_walks` on waypoint POI files
