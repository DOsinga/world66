# City Walks Task

Create at least one walking route for each city. Each walk should be a self-contained piece of writing: an opinionated route through a specific neighbourhood or area that could be followed on foot.

The Amsterdam Jordaan Walk (`content/europe/netherlands/amsterdam/jordaan_walk.md`) is the reference implementation.

## File structure

A walk lives alongside the city's other content:

```
content/{city}/
  city_walks.md         ← section page (create if absent)
  {name}_walk.md        ← the walk itself (e.g. jordaan_walk.md, gothic_quarter_walk.md)
  {waypoint_poi}.md     ← POI files for walk-specific stops (at city root, not in things_to_do/)
```

Walk-specific POIs (memorial trees, small courtyards, quiet canals) go at the city root level. POIs that are significant tourist sights belong in `things_to_do/` instead.

The walk file is tagged `city_walks` (which makes it appear in the `city_walks` section). Individual POI files visited along the route should NOT be tagged `city_walks` — only the walk itself gets that tag.

## Walk file format

```yaml
---
title: The [Name] Walk
type: walk
tags:
  - city_walks
latitude: {approx centre lat}
longitude: {approx centre lon}
waypoints:
  - things_to_do/some_sight    # path relative to city root (no .md)
  - some_walk_specific_poi
route:
  - [lat, lon]
  - [lat, lon]
  ...
---

Body text here.
```

The `route` field is the polyline — a list of [lat, lon] pairs following actual streets. The `waypoints` field lists POI slugs in the order they are visited; these are rendered as markers on the map and as hover cards in the walk text.

## Methodology

Follow this order — don't skip straight to generating coordinates.

### 1. Pick a neighbourhood and a concept

Choose an area with genuine character: a historic quarter, a specific district, a particular architectural or social identity. Decide what the walk is *about* — what a visitor will understand by the end that they couldn't have learned from a guidebook description.

### 2. Identify 5–8 stops along a logical path

The stops should be reachable in sequence without backtracking. Think in terms of what someone walking north-to-south (or along a canal, or through a market) would naturally encounter. Good stops:
- Named sights already in `things_to_do/`
- Specific streets, canals, or squares with their own character
- Small monuments, trees, courtyards, or facades that most guides skip
- Market days, particular corners, neighbourhood boundaries

Query OpenStreetMap via the Overpass API to discover what's actually there:
```
[out:json];
(
  node["historic"](bbox);
  node["tourism"="artwork"](bbox);
  node["amenity"="place_of_worship"]["name"](bbox);
);
out;
```
Replace `bbox` with `{south},{west},{north},{east}` coordinates for the area.

### 3. Route the walk via OSRM

Once you have the stops in order, call the OSRM foot routing API:
```
https://routing.openstreetmap.de/routed-foot/route/v1/foot/{lon1},{lat1};{lon2},{lat2};...?overview=full&geometries=geojson
```
Coordinates are **longitude first, then latitude** in the URL. Convert the returned GeoJSON coordinates ([lon, lat]) to [lat, lon] for the `route` field.

**Remove loops**: OSRM produces out-and-back detours when snapping to waypoints. Scan the coordinate list and remove any segment where the route visits a point and then immediately retraces back to a previous point.

### 4. Write the walk

Write the body as flowing prose — not a bulleted list of stops, not a turn-by-turn itinerary. Each paragraph should cover one stop or transition. Lead with what makes the area worth understanding, not what makes it famous.

Link waypoints using standard markdown links:
```markdown
[Westerkerk](/europe/netherlands/amsterdam/things_to_do/westerkerk)
```
These links get rendered as hover cards showing the POI description.

See STYLE.md for voice and tone. Practical, specific, opinionated. No superlatives.

### 5. Create POI files for walk-specific stops

For each stop that doesn't already have a file:
- Create `{stop_slug}.md` at the city root
- Set `type: poi`, `category:` (Monument, Street, Historic Site, etc.), and accurate `latitude`/`longitude`
- Write 2–4 sentences: what it is, why it matters, what to notice
- Do **not** add `tags: [city_walks]` — only the walk file itself gets that tag

### 6. Create or verify `city_walks.md`

If the city doesn't have `city_walks.md`, create it:
```yaml
---
title: City Walks
type: section
---

[2–4 sentences: why this city rewards walking, what the walks cover.]
```

### 7. Commit

One commit per walk:
```
Add {City} {Name} Walk
```

## Tools

- **Overpass API**: `https://overpass-api.de/api/interpreter` (fall back to `https://overpass.kumi.systems/api/interpreter` if busy)
- **OSRM foot routing**: `https://routing.openstreetmap.de/routed-foot/route/v1/foot/`
- Coordinates for known sights: check existing POI files in `things_to_do/`

## Batch files

Each batch file contains 3–4 cities. Create one walk per city (more if time allows). Commit each walk separately.
