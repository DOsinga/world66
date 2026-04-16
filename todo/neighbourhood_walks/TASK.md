# Neighbourhood Walks Task

Create a single definitive walk for a city neighbourhood by synthesising existing city, story, and architecture walks into one unified route. The result should be the walk you'd recommend if someone asked "what's the one walk I should do in this neighbourhood?" — something that rewards attention to the built environment, carries real historical weight, and tells you something about the city you wouldn't know from standing on a random street corner.

This task assumes that three separate walks already exist for the neighbourhood (city walk, story walk, architecture walk). If only some exist, use those as source material and research the missing angle.

## File structure

The output replaces the three separate walk files with a single file:

```
content/<city-path>/
  <neighbourhood>_walk.md       # replaces: <neighbourhood>_walk.md,
                                #   <neighbourhood>_story_walk.md,
                                #   <neighbourhood>_architecture_walk.md
  <new_waypoint_slug>.md        # new waypoint POIs, if any
```

Delete the story and architecture variants after the new walk is committed.

## Step 1 — Read and understand the source material

Read all three existing walk files for the neighbourhood:

- `<neighbourhood>_walk.md` — the general city walk: character, main sights, feel
- `<neighbourhood>_story_walk.md` — the story walk: historical incidents, specific addresses, named people
- `<neighbourhood>_architecture_walk.md` — the architecture walk: building types, periods, visual vocabulary

For each walk, note:
- Which waypoints are unique to it (not shared with the others)
- Which stories or architectural observations are the most memorable
- What the walk's **connecting thread** is (if it has one)
- Where the route goes and how long it is

## Step 2 — Design the combined walk

The combined walk is not a concatenation. It is a new walk that uses the three as source material. The goal is a route of **2–4 km** with **7–10 waypoints** that does all three things at once: puts you in the right streets, tells you the stories, and teaches you to read the buildings.

### How to select waypoints

Rank every waypoint across all three walks on two axes:

1. **Story weight**: does this stop have a specific, surprising, human story attached to it?
2. **Visual payoff**: is there something to see or point at — a gable, a plaque, a building type contrast?

Prefer stops that score high on both. If a stop scores high on only one, keep it only if it is indispensable for the narrative thread or for route continuity.

A stop that appears in two or three of the source walks is probably essential. A stop that appears in only one is a candidate for cutting unless it provides the walk's best single story or its best single architectural lesson.

**Maximum 10 waypoints.** A walk that tries to include everything includes nothing. Cut until it hurts, then cut one more.

### Narrative thread

The combined walk needs a single thread that can hold the architecture and the stories together. It does not need to be stated explicitly, but it should be present. Examples:
- "A neighbourhood that was built for the city's poor and has always fought for itself"
- "What a city looks like when it grows too fast, and what happens to the people who live there"
- "Three hundred years of building for people who couldn't afford the canal ring"

Name the thread before you start writing. It will determine which details to include and which to cut.

## Step 3 — Verify waypoint coordinates with OSM

For each waypoint retained from the source walks, check whether the existing coordinates are accurate:

```
https://nominatim.openstreetmap.org/search?q=PLACE+NAME+CITY&format=json&limit=1&accept-language=en
```

For a specific building number:
```
https://nominatim.openstreetmap.org/search?q=STREET+NUMBER+CITY&format=json&limit=1&accept-language=en
```

**Nominatim returns area centroids, not street points.** A coordinate for a POI "on" a street may be 50–100m from the actual street, which causes routing to silently follow a parallel street instead. For any waypoint described as being on or at a specific street:

1. Query the street itself to get its actual lat/lng at multiple points:
   ```
   https://nominatim.openstreetmap.org/search?q=STREET+NAME+CITY&format=json&limit=5&accept-language=en
   ```
2. Verify that the waypoint's coordinates are consistent with the street's coordinate band at that location.

For named monuments or buildings with an exact OSM entry, the Overpass API gives more precise results:
```
https://overpass-api.de/api/interpreter?data=[out:json];node["name"="EXACT NAME"](LAT_MIN,LNG_MIN,LAT_MAX,LNG_MAX);out;
```

Add 1–2 seconds of delay between requests to avoid rate limiting. Update any coordinates that are more than ~30m off.

## Step 4 — Get the walking route

The `route:` field is a list of `[lat, lng]` coordinate pairs tracing the actual walking path. Use the OSRM foot router to generate it:

```
https://routing.openstreetmap.de/routed-foot/route/v1/foot/LNG1,LAT1;LNG2,LAT2;...?overview=full&geometries=geojson&steps=true
```

Note: coordinates in the OSRM URL are **`lng,lat`** (reversed). The response `routes[0].geometry.coordinates` is also `[lng, lat]` — swap to `[lat, lng]` before writing into the YAML.

```python
import json, urllib.request, time

waypoints = [(lat1, lng1), (lat2, lng2), ...]  # lat, lng order

coords_str = ";".join(f"{lng},{lat}" for lat, lng in waypoints)
url = f"https://routing.openstreetmap.de/routed-foot/route/v1/foot/{coords_str}?overview=full&geometries=geojson&steps=true"
data = json.loads(urllib.request.urlopen(url).read())
route = [[p[1], p[0]] for p in data["routes"][0]["geometry"]["coordinates"]]
```

### Verify the route follows the intended streets

Request `&steps=true` and check the `steps[].name` field for each leg. If the narrative says "walk along Bloemgracht" but the step names show a parallel canal street, the waypoint coordinates are off. Adjust until the step names match the prose.

### Forcing the route along a specific street

If the walk prose says you traverse the length of a street (e.g. a market, a canal-side boulevard), OSRM will only follow it if forced through it by a waypoint at its far end. Add a **forcing waypoint** (not a named stop) in the OSRM URL at the far end of the street. Do not include it in the `waypoints:` list in the walk file.

### Avoiding backtracking

If longitude (or latitude) values oscillate back and forth in the route output, the route is doubling back. Fix by:
- Reordering waypoints so the walk progresses in one direction
- Splitting into separate OSRM calls and stitching the segments
- Placing named waypoints at the *entry* of a stretch rather than mid-stretch

### Sanity check

After generating the route:
- First point should be within ~50m of waypoint 1; last point within ~50m of the final waypoint
- Longitude values should progress mostly in one direction (or describe a clean loop), not oscillate
- All coordinates should fall within the neighbourhood's bounding box
- Check OSRM step names for any leg where you are not sure the route is correct

## Step 5 — Write the walk

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
  - things_to_do/existing_poi   # existing POIs use their section path
  - new_waypoint_slug           # new POIs at city root, just slug
route:
  - [52.123456, 4.123456]
  - ...
---
```

### Prose

The body is a narrative walk — not a list, not a Wikipedia summary. Each paragraph covers one or two waypoints. The three source walks have already done the research; your job is to weave them into a single continuous voice.

**Open** by naming the neighbourhood's character and why it rewards walking — its history in one or two sentences, its feel today, what you will understand by the end that you didn't at the start.

**At each waypoint**, combine what all three source walks know about this stop. A good combined stop has:
- The specific thing to look at (visible detail — gable type, plaque, door number)
- The story behind it (a name, a date, something surprising)
- What it tells you about the neighbourhood more broadly

Not every stop needs all three. But a stop that is only one of them — only architectural observation, only story, only general colour — is probably not the best use of a waypoint slot.

**Transitions** describe the streets between stops. Name the streets. Describe what you pass. The route is content.

**Close** with the final waypoint and something that lingers: a question, an irony, a detail. Do not summarise; let the last stop do the work.

**End with**: "The walk is approximately X km and takes about Y hours at a comfortable pace, longer if [specific reason]."

### Tone

Draw on the three source walks:
- **City walk tone**: direct, oriented to the visitor, practical about what to notice
- **Story walk tone**: specific names and numbers, irony welcome, let facts speak
- **Architecture walk tone**: name the term, point at the detail, explain what it means

The combined walk uses all three registers, moving between them as the stops demand. A hofje courtyard needs the architectural eye and the social history. A riot memorial needs the story and the neighbourhood context. A market needs the feel and the human anecdote.

### Waypoint POI files

For any new waypoints not already in a city section, create a file at the city root:

```yaml
---
title: "Sint Andrieshofje"
type: poi
latitude: 52.3756
longitude: 4.8812
---

A 17th-century hofje at Egelantiersgracht 107...
```

2–4 sentences. Visible detail + one piece of context.

**Do not add `tags: - city_walks` to waypoint POI files.**

## Step 6 — Replace the source files

After the new walk is committed and verified:

1. Delete the three source walk files:
   ```
   git rm content/<city-path>/<neighbourhood>_story_walk.md
   git rm content/<city-path>/<neighbourhood>_architecture_walk.md
   ```
   (The city walk file `<neighbourhood>_walk.md` is replaced in place by the new file.)

2. Commit the deletion separately:
   ```
   Complete neighbourhood_walks/<shard>: delete superseded story and architecture walks
   ```

## Step 7 — Commit

```
Neighbourhood walk: [City] — [Neighbourhood]

- X waypoints, Y km, Z hours
- Combines: [neighbourhood]_walk, [neighbourhood]_story_walk, [neighbourhood]_architecture_walk
- Thread: [one line describing the connecting thread]
- N new/updated waypoint POIs
```

One commit per neighbourhood.

## Quality checklist

- [ ] Narrative thread named before writing
- [ ] Waypoints selected by story weight + visual payoff, not by inclusion in source walks
- [ ] Maximum 10 waypoints
- [ ] All waypoint coordinates verified against Nominatim; corrected if >30m off
- [ ] OSRM route generated using `routing.openstreetmap.de/routed-foot`
- [ ] OSRM step names checked (`&steps=true`) for each leg where the intended street matters
- [ ] No backtracking in the route (no oscillating lat/lng values)
- [ ] Route starts and ends within ~50m of first and last waypoints
- [ ] Each stop has at least one visible/specific detail and one story element
- [ ] Prose names streets in transitions
- [ ] Walk ends with distance and time estimate
- [ ] `city_walks.md` section exists in the city root
- [ ] No `tags: - city_walks` on waypoint POI files
- [ ] Source story and architecture walk files deleted in a follow-up commit
