# Story Walks Task

Create a guided walking route built around remarkable true stories — crimes, disasters, obsessions, betrayals, unlikely triumphs — that happened at specific places in a city. The route connects the locations where those stories unfolded. The result reads like a tour guide who has done the research: someone who stops you in front of an unremarkable façade and makes you see it differently.

See the Jordaan Walk (`content/europe/netherlands/amsterdam/jordaan_walk.md`) as the reference for file structure and routing. The difference is in how the walk is chosen and written.

## File structure

```
content/<city-path>/
  city_walks.md              # section page (create if missing)
  <walk_slug>.md             # the walk itself (type: walk)
  <waypoint_slug>.md         # one file per new waypoint POI
```

## Step 1 — Find the stories first

Do not start with a neighbourhood. Start with stories.

Search for:
- Crimes, scandals, and trials that took place at specific addresses
- Buildings with hidden or ironic histories (the bank that went bankrupt, the hospital that killed patients, the church built by someone who was excommunicated)
- Streets or squares named for people whose actual stories contradict the honour
- Places where famous people did something unexpected, embarrassing, or uncharacteristic
- Sites of disasters, fires, floods, explosions — and what replaced them
- Locations connected to a single obsessive person: the collector, the forger, the fanatic
- Places that look ordinary but were once something completely different
- Coincidences of geography: two enemies who lived on the same street, a prison next to a school

Good story sources for a city:
- Search `[city] true crime history`, `[city] historical scandal`, `[city] strange history`, `[city] forgotten history`
- Wikipedia's "History of [city]" article, then drill into specific incidents
- Look for books like "Secret [City]" or "[City] Untold" — their chapter titles reveal the best material
- Local newspaper archives, especially reports from 50–150 years ago
- The footnotes of famous events: what happened to the building afterward?

**The test for a good story**: can you start a sentence with "What most people don't know is..." and have something genuinely surprising follow? If yes, it belongs on this walk.

Collect 8–12 candidate stories before choosing 5–8. Discard the ones that are merely interesting. Keep the ones that are surprising, ironic, or human in a way that lands when you're standing on the spot.

## Step 2 — Build the walk around the stories

Once you have the stories, map the locations. A good story walk:
- Covers 1–3 km (people will stop and listen; they don't want to sprint)
- Has stories that are distributed along the route, not all clustered at one end
- Has variety in story *type*: not six crimes in a row, not five "and then they died" endings
- Has at least one story where the physical place itself is part of the reveal — where standing *there* matters, where you can point at something specific

The walk doesn't need to be in one neighbourhood. It can cross boundaries if the stories pull it across. What it needs is a **connecting theme** — even a loose one. Examples:
- A walk about money: the people who made it, lost it, stole it, and were ruined by it
- A walk about a single decade: what was this city like in the 1920s?
- A walk about women who were erased: whose name *should* be on these streets?
- A walk about things that burned down — and why
- A walk with no theme at all, just story after story, each one stranger than the last

The walk title can reflect the theme if there is one, but a simple descriptive title is fine too.

## Step 3 — Research each story thoroughly

For each waypoint, you need:
- **The story itself**: what happened, when, who was involved, what the consequences were
- **The specific detail that makes it vivid**: a number, a name, a quote, an object, a coincidence
- **What to look for on the spot**: the plaque that gets the date wrong, the bricked-up window, the modern building that replaced the one that burned
- **What happened next**: the story doesn't end at the address — where did it go?

Use web search extensively. Cross-reference. If a story sounds too good to be true, verify it. Do not invent details.

The POI description (2–4 sentences in the waypoint file) is the compressed version. The walk prose is where the story gets told properly.

## Step 4 — Pick waypoints and get coordinates

For each stop, check whether a POI file already exists in the city's sections (`things_to_do/`, `bars_and_cafes/`, etc.). If so, reference it as `things_to_do/slug` in the `waypoints:` list. If not, create a new POI file at the city root.

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
title: "The [Theme or Area] Walk"
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

Write like a tour guide who has done the research and loves the material. Not a textbook. Not a Wikipedia summary. Someone talking.

**The opening** names what kind of walk this is and why it's worth an hour of someone's afternoon. Don't explain the route. Drop them into the world immediately.

**At each stop**, the structure is roughly:
1. Orient them: what are they looking at right now?
2. The setup: what did everyone think was happening here?
3. The reveal: what was actually happening?
4. The specific detail that makes it real: a number, a name, a date, an object
5. The aftermath: what happened next, and does any trace remain?

Not every stop needs all five. Some stories are short. But every stop needs at least the reveal — the thing that makes someone stop walking and say "wait, really?"

**Transitions between stops** are not dead space. Use them to sustain the atmosphere: "Two minutes' walk north, past the building where he later died destitute..." The route itself is part of the story.

**The close** should leave something unresolved or unanswered — a question, an irony, something that will still be in the reader's head when they get home.

**End with distance and time**: "The walk is approximately X km and takes about Y minutes at a comfortable pace."

### Tone

- Direct address ("you are now standing outside...") is fine for orienting, but don't overdo it
- Specific numbers are more convincing than vague amounts: "48,000 guilders" beats "a large sum"
- Name people. "The owner" is forgettable. "Jan Hendrik de Roo, who had embezzled the money over eleven years" is not.
- Irony is welcome; mockery is not. These are real people, even if they did terrible things
- Don't editorialize ("shockingly," "incredibly"). Let the facts speak. If a fact isn't surprising on its own, it's not the right fact.

### Waypoint POI files

For new waypoints, create a file at the city root:

```yaml
---
title: "De Nederlandsche Bank (1763 building)"
type: poi
latitude: 52.3756
longitude: 4.8812
---

The original site of the bank that collapsed in 1763, triggering the first documented international credit crisis. The building that replaced it still stands; the plaque on the wall describes the current tenant and says nothing about the crash.
```

The POI body is the compressed version of the story — 2–4 sentences. It appears as a tooltip on the map and as a linked stop in the walk. It should leave the reader wanting the full version.

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
Story walk: [City] — [Walk Name]

- X waypoints, Y km
- N new waypoint POIs created
- Theme: [one line describing the connecting thread]
```

One commit per walk.

## Quality checklist

- [ ] Each waypoint has a story, not just a description
- [ ] Each story has at least one specific detail (name, number, date, quote)
- [ ] The opening names what kind of walk this is
- [ ] At least one stop has something to physically look for on the spot
- [ ] The close leaves something unresolved
- [ ] All waypoints have `latitude` and `longitude`
- [ ] Route coordinates are `[lat, lng]` (not `[lng, lat]`)
- [ ] Route starts near waypoint 1 and ends near the last waypoint
- [ ] OSRM step names verified — route follows the intended streets
- [ ] All links in the prose point to real pages
- [ ] Walk body ends with distance and time estimate
- [ ] `city_walks.md` section exists in the city root
