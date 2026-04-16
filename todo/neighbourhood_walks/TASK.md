# Neighbourhood Walks Task

Create a single definitive walk for a city neighbourhood, starting from scratch. The result should be the walk you'd recommend if someone asked "what's the one walk I should do in this neighbourhood?" — something that puts you in the right streets, tells you the stories, teaches you to read the buildings, and occasionally stops you in front of something you didn't expect.

Each item in the batch file is a neighbourhood path, e.g. `europe/netherlands/amsterdam/jordaan`. The neighbourhood page exists in `content/` as a starting point for context; everything else is researched fresh.

## File structure

```
content/<city-path>/
  city_walks.md              # section page (create if missing)
  <neighbourhood>_walk.md    # the walk (type: walk)
  <waypoint_slug>.md         # one file per new waypoint POI
```

## Step 1 — Understand the neighbourhood

Read the neighbourhood page at `content/<neighbourhood-path>.md` for a starting overview.

Then run web searches to build a fuller picture. Do all four of the following:

### 1a — Character and history

```
"[neighbourhood] [city] history"
"[neighbourhood] [city] guide"
"[neighbourhood] [city] what to see"
```

You are looking for: what makes this area distinct, when it was built, who lived here, what it is known for, what has changed. Read at least 3 sources before moving on.

### 1b — Stories

```
"[neighbourhood] [city] true history"
"[neighbourhood] [city] historical incident"
"[neighbourhood] [city] famous residents"
"[neighbourhood] [city] strange history" OR "hidden history"
```

You are looking for: crimes, disasters, obsessions, betrayals, unlikely triumphs — events that happened at a specific address and that most visitors don't know about. The test for a good story: can you start a sentence with "What most people don't know is..." and have something genuinely surprising follow? If yes, it belongs on the walk.

### 1c — Architecture

```
"[neighbourhood] [city] architecture"
"[neighbourhood] [city] notable buildings"
"[neighbourhood] [city] architectural history"
"[architect name] [neighbourhood]" — for architects associated with the area
```

For the Netherlands, also search: `rijksmonument [neighbourhood] [city]`, `Amsterdamse School [neighbourhood]`

You are looking for: buildings that are worth stopping at because they teach you something visible — a gable type, a structural detail, a contrast with the building next door. A good architectural stop has something you can point at from the pavement.

### 1d — Street art and murals (if relevant)

```
"[neighbourhood] [city] street art"
"[neighbourhood] [city] murals"
"[neighbourhood] [city] graffiti art"
```

Not every neighbourhood has street art worth including. Only pursue this angle if the search results suggest it is genuinely present and significant. A mural is worth a waypoint if it is large and permanent, has an interesting commissioning story, or marks something about the neighbourhood's identity. Skip this angle entirely if the results are thin.

## Step 2 — Build a candidate list

Before selecting waypoints, compile a list of **at least 12 candidates** across all relevant angles. For each candidate, note:

- **Name / address**: what it is and where
- **Angle(s)**: character, story, architecture, street art — it may hit more than one
- **The specific thing**: what you would say to someone standing in front of it — the story, the detail to look at, the thing that makes it worth stopping for
- **Source**: where you found this

Do not proceed to Step 3 until you have 12 candidates. Candidates from web search are welcome; invented or unverified details are not.

## Step 3 — Select waypoints

From the candidate list, select **7–10 waypoints** for the walk.

### Selection criteria

Prefer candidates that:
- Score on **more than one angle** — a building that has a great story *and* something worth looking at is worth two stops combined into one
- Have something **specific and visible** — a plaque, a door number, a particular window, a mural panel. "An interesting neighbourhood" is not a waypoint. "The building at number 107, where the gate leads to a courtyard that most people walk past" is.
- **Spread across the walk route** — don't cluster all the best stops at one end

Cut candidates that:
- Are only vaguely interesting ("a typical example of 19th-century housing")
- Duplicate another stop (two examples of the same gable type, two stories of the same type)
- Require a significant detour that isn't justified by the stop's quality

**The walk needs a thread.** It doesn't need to be stated explicitly, but before writing you should be able to name it in one sentence. Examples:
- "A neighbourhood built for the city's poor that has always known how to fight back"
- "Three hundred years of building compressed into ten blocks"
- "What a city looks like when it grows too fast and who gets left behind"

Name the thread before writing. It will determine which details to keep and which to cut.

## Step 4 — Get waypoint coordinates from OSM

For each waypoint, get accurate coordinates using the Nominatim API:

```
https://nominatim.openstreetmap.org/search?q=PLACE+NAME+CITY&format=json&limit=1&accept-language=en
```

For a specific street address:
```
https://nominatim.openstreetmap.org/search?q=STREET+NUMBER+CITY&format=json&limit=1&accept-language=en
```

For a named monument or building with an exact OSM entry:
```
https://overpass-api.de/api/interpreter?data=[out:json];node["name"="EXACT NAME"](LAT_MIN,LNG_MIN,LAT_MAX,LNG_MAX);out;
```

Add 1–2 seconds between requests to avoid rate limiting.

**Critical: Nominatim returns area centroids, not street points.** A coordinate for a POI described as being "on" a specific street may be 50–100m away from that street. This causes the OSRM router to silently follow a parallel street instead.

For any waypoint that needs to be at a precise location on a named street:

1. Query the **street itself** to get its actual lat/lng range:
   ```
   https://nominatim.openstreetmap.org/search?q=STREET+NAME+CITY&format=json&limit=5&accept-language=en
   ```
   This returns multiple points along the street — verify that the waypoint's lat is within the street's lat band at that longitude.

2. After routing, check OSRM step names (see Step 5) to confirm the route follows the correct street. If it names a parallel street, the waypoint coordinate is off — adjust until it lands on the right street.

## Step 5 — Get the walking route

The `route:` field is a list of `[lat, lng]` coordinate pairs tracing the actual walking path through the streets.

Use the OpenStreetMap foot router — **not** `router.project-osrm.org`, which can produce multi-kilometre detours. Use:

```
https://routing.openstreetmap.de/routed-foot/route/v1/foot/LNG1,LAT1;LNG2,LAT2;...?overview=full&geometries=geojson&steps=true
```

Coordinates in the URL are **`lng,lat`** (reversed). The response `routes[0].geometry.coordinates` is also `[lng, lat]` — swap to `[lat, lng]` before writing into the YAML.

```python
import json, urllib.request, time

waypoints = [(lat1, lng1), (lat2, lng2), ...]  # your waypoints in walk order

coords_str = ";".join(f"{lng},{lat}" for lat, lng in waypoints)
url = (f"https://routing.openstreetmap.de/routed-foot/route/v1/foot/{coords_str}"
       f"?overview=full&geometries=geojson&steps=true")
data = json.loads(urllib.request.urlopen(url).read())

# Swap lng,lat → lat,lng
route = [[p[1], p[0]] for p in data["routes"][0]["geometry"]["coordinates"]]

# Print for YAML
for pt in route:
    print(f"  - [{pt[0]:.6f}, {pt[1]:.6f}]")

# Verify street names
for leg in data["routes"][0]["legs"]:
    for step in leg["steps"]:
        if step["name"]:
            print(f"  → {step['name']}")
```

### Verify the route follows the intended streets

The `steps[].name` output shows which street each segment of the route is on. Check every leg where the walk prose describes walking along a specific street. If the step names show a parallel street, the waypoint coordinates are off — adjust until the names match.

### Forcing the route along a street

If the prose says you walk the length of a street (a market, a canal, a boulevard), OSRM will only traverse it if forced by a waypoint at the far end. Add a **forcing waypoint** — a coordinate just past the far end of the street — in the OSRM URL. Do not include it in the `waypoints:` list in the walk file.

### Avoiding backtracking

If the longitude (or latitude) values in the route output oscillate back and forth around the same value, the route is doubling back. Fix by:
- Reordering waypoints so the walk progresses in one direction
- Splitting into separate OSRM calls and stitching the segments
- Placing named waypoints at the *entry* of a stretch rather than mid-stretch

### Sanity check

- First route point should be within ~50m of waypoint 1; last route point within ~50m of the final waypoint
- Lat/lng values should not oscillate — the route should progress in a consistent direction or describe a clean loop
- All coordinates should fall within the neighbourhood's rough bounding box

## Step 6 — Write the walk

### The walk file

```yaml
---
title: "The [Neighbourhood] Walk"
type: walk
tags:
  - city_walks
latitude: <start lat>
longitude: <start lng>
waypoints:
  - things_to_do/existing_poi   # POIs that exist in a section: use section/slug
  - new_waypoint_slug           # new POIs at city root: just slug
route:
  - [52.123456, 4.123456]
  - ...
---
```

### Prose

The body is a narrative walk — not a list, not a Wikipedia summary. Each paragraph covers one or two waypoints. The opening establishes the neighbourhood's character and why it rewards walking. Each stop has the specific thing to notice, the story or context behind it, and (where the architecture warrants it) what it tells you about how the place was built. Transitions describe the streets between stops. The close ends with the final waypoint and something that lingers.

**Opening**: one or two sentences on what this neighbourhood is and why it is worth an hour on foot. Drop the reader into the world immediately — name the specific thing that makes this area different from the rest of the city.

**At each waypoint**: lead with what the reader is looking at. Then give them something they didn't know — the story, the detail, the term. Do not editorialize ("remarkably," "fascinatingly"); let the specific fact do the work.

**Transitions**: name the streets you walk between stops. The route is content — describe what you pass, what the neighbourhood looks like at street level.

**Mixing angles**: not every stop needs all four angles. A hofje courtyard needs the architecture and the social history. A riot memorial needs the story and the neighbourhood context. A market needs the feel and the human anecdote. A mural needs the artist's name and why it was commissioned here. Move between registers as the stops demand — the walk should not feel like three separate walks stitched together.

**Close**: end with the final waypoint. Do not summarise the walk. Let the last stop do the work — an unanswered question, an irony, a detail that changes how the walk looks in retrospect.

**Final sentence**: "The walk is approximately X km and takes about Y hours at a comfortable pace, longer if [specific reason — climbing a tower, entering a courtyard, staying for the market]."

### Tone

- Specific is better than vague: "26 people killed in three days of fighting" beats "violent clashes"
- Name people: "Ernst Cahn, who was shot on 3 March 1941" is more useful than "a Jewish refugee"
- Architectural terms are welcome if explained on first use and pointed at something visible
- Irony is welcome; mockery is not
- Direct address ("you are now standing...") is fine for orienting, but use it sparingly

### Waypoint POI files

For waypoints not already in a city section, create a file at the city root:

```yaml
---
title: "Sint Andrieshofje"
type: poi
latitude: 52.3756
longitude: 4.8812
---

A 17th-century hofje at Egelantiersgracht 107 — a gate in the street wall that most people walk past. Step through and a covered passage leads into a courtyard of whitewashed walls and complete quiet. Funded by a wealthy merchant as an almshouse for elderly widowed women; residents received a room in exchange for good conduct and church attendance.
```

2–4 sentences: the specific visible thing + one piece of context. It appears as a tooltip on the map.

**Do not add `tags: - city_walks` to waypoint POI files.** Only the walk file itself carries that tag.

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
Neighbourhood walk: [City] — [Neighbourhood]

- X waypoints, Y km, ~Z hours
- Angles covered: [character / stories / architecture / street art]
- Thread: [one line]
- N new waypoint POIs created
```

One commit per neighbourhood.

## Quality checklist

- [ ] At least 12 candidates researched before selecting waypoints
- [ ] Narrative thread named before writing
- [ ] 7–10 waypoints selected; no two stops that duplicate the same angle in the same way
- [ ] Street art angle either included with a genuine stop, or explicitly skipped because search results were thin
- [ ] All waypoint coordinates fetched from Nominatim or Overpass — not guessed
- [ ] Street-facing coordinates verified against Nominatim street query where needed
- [ ] OSRM route via `routing.openstreetmap.de/routed-foot`
- [ ] OSRM step names checked for every leg where intended street matters
- [ ] No backtracking (no oscillating lat/lng values)
- [ ] Route starts and ends within ~50m of first and last waypoints
- [ ] Each stop has at least one specific visible detail or specific fact
- [ ] Transitions name the streets walked between stops
- [ ] Walk ends with distance and time estimate
- [ ] `city_walks.md` section exists in the city root
- [ ] No `tags: - city_walks` on waypoint POI files
