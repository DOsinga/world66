# City Walks Task

Create a guided walking route for a city, with a route polyline, numbered waypoints, waypoint POI files, and narrative prose connecting them.

See the Jordaan Walk (`content/europe/netherlands/amsterdam/jordaan_walk.md`) as the reference implementation.

## File structure

```
content/<city-path>/
  city_walks.md              # section page (create if missing)
  <walk_slug>.md             # the walk itself (type: walk)
  <waypoint_slug>.md         # one file per new waypoint POI
```

## Step 1 — Choose a walk

Pick a neighbourhood or area that:
- Is compact and walkable (1–3 km)
- Has a distinct character and history
- Has at least 5–8 points of interest within walking distance
- Is not already covered by an existing walk in `city_walks/`

Use web search to understand the area: its history, key streets, notable buildings, hidden corners. The best walks have a narrative thread — not just a list of sights, but a story about a place.

## Step 2 — Pick waypoints

Identify 5–9 stops that together tell the story of the area. Mix:
- Anchor sights (church, market, main square)
- Quieter discoveries (a courtyard, a sculpture, a specific tree or building)
- Things that explain something about the city's history or character

For each waypoint, check whether a POI file already exists in the city's sections (`things_to_do/`, `bars_and_cafes/`, etc.). If so, reference it as `things_to_do/slug` in the `waypoints:` list. If not, create a new POI file at the city root.

### Getting waypoint coordinates from OSM

Use the Nominatim API to find coordinates for named places:

```
https://nominatim.openstreetmap.org/search?q=PLACE+NAME+CITY&format=json&limit=1&accept-language=en
```

For precise locations (a specific building entrance, a monument), use the Overpass API:

```
https://overpass-api.de/api/interpreter?data=[out:json];node["name"="EXACT NAME"](LAT_MIN,LNG_MIN,LAT_MAX,LNG_MAX);out;
```

Add 1–2 seconds of delay between requests to avoid rate limiting.

Each waypoint POI file needs `latitude` and `longitude`. Without them the marker won't appear on the map.

**Critical: Nominatim returns area centroids, not street points.** A POI described as being "on" a street may have coordinates that are 50–100m away from the actual street. This causes routing to silently follow a parallel street instead. Always verify coordinates that need to be on a specific street:

1. Query Nominatim for the **street itself** (not just the POI) to get actual street coordinates:
   ```
   https://nominatim.openstreetmap.org/search?q=STREET+NAME+CITY&format=json&limit=5&accept-language=en
   ```
   This returns multiple points along the street — use these to verify the POI lat is close to the street's actual lat at that longitude.

2. After routing, **check OSRM step names** to confirm the route follows the intended street:
   ```
   ?overview=full&geometries=geojson&steps=true
   ```
   The `steps[].name` field shows which street each segment is on. If it shows the wrong street name, the waypoint coordinates are wrong.

## Step 3 — Get the walking route

The `route:` field is a list of `[lat, lng]` coordinate pairs that trace the actual walking path through the streets. This is what draws the red line on the map.

### Using OSRM to get a route

Build a coordinate string from your waypoints in order (lng,lat — note the reversed order for OSRM):

```
https://router.project-osrm.org/route/v1/foot/LNG1,LAT1;LNG2,LAT2;LNG3,LAT3?overview=full&geometries=geojson
```

The response contains `routes[0].geometry.coordinates` — a list of `[lng, lat]` pairs. **Swap them to `[lat, lng]`** for the YAML frontmatter.

Example Python to decode and format:
```python
import json, urllib.request, time

waypoints = [
    (52.3742, 4.8840),  # lat, lng for each stop
    (52.3756, 4.8815),
    (52.3782, 4.8830),
]

coords_str = ";".join(f"{lng},{lat}" for lat, lng in waypoints)
url = f"https://router.project-osrm.org/route/v1/foot/{coords_str}?overview=full&geometries=geojson"
data = json.loads(urllib.request.urlopen(url).read())
route = [[p[1], p[0]] for p in data["routes"][0]["geometry"]["coordinates"]]
print("route:")
for pt in route:
    print(f"  - [{pt[0]:.6f}, {pt[1]:.6f}]")
```

OSRM returns many points along the streets. This is correct — more points means a smoother, more accurate line on the map.

### When the prose says "walk along a street"

If the narrative describes walking the length of a street (e.g. a market street, a canal-side boulevard), the route **must physically traverse that street** — not cut across it or skip to a parallel path. OSRM will only follow a street if forced through it by intermediate waypoints.

**Forcing waypoints must be on the correct street.** Use Nominatim to query the street itself and get its actual lat/lng at multiple points. Do not rely on the coordinates of a POI *near* the street — those are often the centroid of a named area and can be 50m off. Compute intermediate forcing points by interpolating along the Nominatim-verified street line.

OSRM will only follow a street if it is forced to stop at a point beyond the far end of it.

**How to do it:**

1. Add a *forcing waypoint* at the far end of the street in your OSRM request — a coordinate just past where the street exits, not a named stop in the walk.
2. Use that forcing waypoint only in the OSRM URL. The `waypoints:` list in the walk file only includes the named stops.
3. Route separate segments if needed to avoid backtracking (see below).

**Avoiding backtracking:**

OSRM sometimes creates U-turns when a waypoint sits mid-route and the next stop is back the way you came. Check the coordinates: if the longitude (or latitude) oscillates back and forth around the same value, the route is doubling back. Fix this by:

- Splitting into separate OSRM calls and stitching the segments: route A→B→C cleanly, then C→D→E cleanly, join them.
- Reordering waypoints so the walk progresses in one direction (e.g. west-to-east, or a loop that never reverses).
- Placing the named waypoint at the *entry* of a street, not the exit, so OSRM continues forward after it.

**Use routing.openstreetmap.de, not router.project-osrm.org:**

The public `router.project-osrm.org` foot profile can produce wildly wrong routes in some cities (multi-kilometre detours for 200m segments). Use `routing.openstreetmap.de/routed-foot` instead — it uses the same OSRM format but a better-maintained foot graph:

```
https://routing.openstreetmap.de/routed-foot/route/v1/foot/LNG1,LAT1;LNG2,LAT2?overview=full&geometries=geojson
```

### Sanity-check the route

Verify the route makes sense: the coordinates should all fall within the city's bounding box and trace a logical path between the waypoints. A quick check:
- The first and last points should be near the first and last waypoints.
- Plot the longitude values in order — they should progress mostly in one direction. A value that reverses and repeats is a sign of backtracking.
- The route should reach the far end of any street the prose says you walk.

## Step 4 — Write the walk

### The walk file (`<slug>.md`)

```yaml
---
title: "The [Area] Walk"
type: walk
tags:
  - city_walks
latitude: <start lat>
longitude: <start lng>
waypoints:
  - things_to_do/existing_poi   # reference existing POIs with their section path
  - new_waypoint_slug           # new POIs created at city root, just slug
route:
  - [52.123456, 4.123456]
  - ...
---
```

### Prose style

The body is a narrative walk, not a list. Each paragraph covers one or two waypoints and tells you something worth knowing before you arrive.

- **Open** with what makes this area distinctive — its history, its feel, why it rewards walking.
- **At each waypoint**: the specific thing to notice, the story behind it, what to look for. Not just "here is X" but "here is X, and this is why it matters."
- **Transitions**: describe the streets between waypoints. The route itself is content — what do you walk past? What does the neighbourhood look like at street level?
- **Close** with the final waypoint and something that lingers: a view, a detail, a question the walk leaves open.
- **End with distance and time**: "The walk is approximately X km and takes about Y minutes at a comfortable pace."

Use specific street names, building numbers, dates. Link to waypoints on first mention: `[Westerkerk](/city-path/things_to_do/westerkerk)`.

Research everything with web search. Do not invent names, dates, or anecdotes.

### Waypoint POI files

For new waypoints (not already in a city section), create a file at the city root:

```yaml
---
title: "Sint Andrieshofje"
type: poi
latitude: 52.3756
longitude: 4.8812
---

A 17th-century hofje (almshouse courtyard) at Egelantiersgracht 107...
```

Keep the body short (2–4 sentences). It appears as a tooltip on the map and as a linked stop in the walk.

**Do not add `tags: - city_walks` to waypoint POI files.** That tag makes them appear as items in the city_walks section listing, alongside the walks themselves. Waypoint POIs are reached via the walk's waypoints list, not by browsing the section. Only the walk file itself should carry `tags: - city_walks`.

## Step 5 — Create the section file (if missing)

If `city_walks.md` doesn't exist in the city root:

```yaml
---
title: "City Walks"
type: section
---

Guided walks through [city]'s most distinctive neighbourhoods, with routes, waypoints, and things to look out for along the way.
```

## Step 6 — Commit

```
City walk: [City] — [Walk Name]

- X waypoints, Y km
- N new waypoint POIs created
```

One commit per walk.

## Quality checklist

- [ ] All waypoints have `latitude` and `longitude`
- [ ] Route coordinates are `[lat, lng]` (not `[lng, lat]`)
- [ ] Route starts near waypoint 1 and ends near the last waypoint
- [ ] Waypoints listed in the order you encounter them on the route
- [ ] All links in the prose point to real pages
- [ ] Walk body ends with distance and time estimate
- [ ] `city_walks.md` section exists in the city root
