# Regions Map — Design Notes

A "visited places" world map served at `/regions/`. The world is divided into
~440 polygons; click one to mark it visited (saturated colour, persisted in
localStorage); search/filter by name; click through to the underlying World66
location pages for the destinations inside.

The interesting part is how the polygons are built — not by country, but by an
importance-weighted Voronoi tessellation seeded by the World66 location
scores. This doc walks through the pipeline so it can be picked up later.

## What's where

```
regions_app/                                  Django app for /regions/
  views.py, urls.py                           one view, one URL
  templates/regions_app/map.html              the whole frontend (Leaflet)

static/geo/regions.geo.json                   ~440 region polygons (built)
static/geo/regions_data.json                  region_id -> {name, parent,
                                                top_locations, ...} (built)

tools/build_regions.py                        main pipeline (run to rebuild)
tools/raw/ne_50m_admin_0_map_subunits.geojson Natural Earth source data
tools/region_name_overrides.json              human-curated cell names
tools/apply_region_names.py                   one-shot: /tmp/region_names_out/
                                                -> region_name_overrides.json
```

The dev server runs `python manage.py runserver 8066`. The page lives at
`http://127.0.0.1:8066/regions/`.

## Pipeline overview

```
content/**/*.md                Natural Earth subunits
   (loc_type, lat, lon, score)        (308 polygons; sovereign countries
       |                               split into territories — Greenland,
       |                               French Guiana, Hawaii, etc.)
       |                                       |
       v                                       v
   load_locations()                     load_subunits()
       |                                       |
       v                                       v
   importance = 10**(score*K)        assign_locations_to_subunits()
       |                                       |
       +---------------------------------------+
                       |
                       v
       For each subunit:
         total importance > BUDGET ?
           yes -> split_subunit()  --> k-means centroids
                                       label each loc by nearest centroid
                                       Voronoi over EVERY loc
                                       unary_union cells per label
                                       clip to subunit polygon
           no  -> keep whole, named after the Natural Earth subunit
                       |
                       v
              render_outputs():
                apply region_name_overrides.json
                drop country/continent pages from top_locations
                write regions.geo.json + regions_data.json
```

## Step by step

### 1. Load scored locations

`load_locations()` in `tools/build_regions.py` walks `content/**.md` and keeps
every page with `loc_type` in `{city, country, region}` that also has
`score`, `latitude`, `longitude`. Returns ~6,600 `Loc` dataclasses.

Country and region pages are loaded so they can affect importance budgets,
but they're filtered out of display in step 5 (countries shouldn't appear as
"destinations inside" their sub-regions).

### 2. Importance transform

```python
importance = 10 ** (score * IMPORTANCE_K)   # K = 4.0
```

Raw scores cluster between 0.3 and 0.7 — too flat for our purposes. The
exponent spreads them: score 0.5 → 100, 0.7 → 631, 0.9 → 3,981, 1.0 →
10,000. Top destinations dominate; small towns barely register. World total
≈ 1.3 million.

### 3. Subunits from Natural Earth

`tools/raw/ne_50m_admin_0_map_subunits.geojson` is the "admin 0 — map
subunits" layer from Natural Earth. 308 polygons. The reason we use this and
not plain countries: subunits keep overseas territories separate (Réunion,
Martinique, French Guiana, Hawaii, Puerto Rico, Greenland, Bornholm,
Macao, …) which is exactly what a "visited places" app wants.

Locations are point-in-polygon assigned to subunits using a `shapely`
STRtree, falling back to nearest subunit for coastline/geocoding offsets.

### 4. Decide split vs keep

For each subunit:

```python
n_splits = round(total_importance / BUDGET)   # BUDGET = 6000
```

- `n_splits <= 1` or fewer than 4 locations → keep whole, name = NE subunit
  name. The vast majority (260 of 440) of regions are unsplit subunits.
- Otherwise → split via `split_subunit()`.

### 5. Splitting: organic-border Voronoi (the interesting bit)

The naïve approach — Voronoi cells from the top-N cities — produces
visually-straight cell borders and weird name geography (e.g. Hamburg
landing inside Rothenburg ob der Tauber's cell because there's no seed in
the north). We do three things differently:

1. **Importance-weighted k-means** picks the K centroids. Initialised with
   the top-K cities, then Lloyd's iterations move each centroid to the
   importance-weighted mean of its assigned locations. The centroids drift
   toward city *density* rather than tourist *hotspots*, so northern
   Germany gets a centroid even when no individual northern German city
   ranks in the top 5.

2. **Voronoi over every location, not just centroids.** We tessellate the
   subunit using all of its location points, then label each cell by which
   centroid its seed point is closest to.

3. **`shapely.ops.unary_union`** merges cells sharing a label into one
   (possibly multi-) polygon. The resulting borders follow the local
   Voronoi tessellation between actual cities, producing jagged, organic
   region boundaries instead of straight lines between centroids.

All cells are then clipped to the subunit polygon so they respect country
borders.

The flag `is_split: True` is added so downstream code can tell whole
subunits from split cells.

### 6. Naming

There are two naming sources:

- **Unsplit subunits**: use the Natural Earth `NAME` (Madagascar, Greenland,
  Hawaii, Bornholm, Mayotte, …). These are real geographic/political units
  and the NE name is almost always the right one.
- **Split cells**: human-curated names from `tools/region_name_overrides.json`.

How the overrides file got built:

1. After the first build, every split cell was named after its top-scoring
   location ("Key West" for the cell covering most of Florida; "Riomaggiore"
   for Cinque Terre). Awful.
2. For each of the 47 countries with multi-cell splits, we launched a
   subagent with the cell + its top destinations and asked for a 1–4 word
   touristy name. The agent has full country context, so it could pick
   consistent names across all of e.g. France's cells (Provence, French
   Riviera, Loire Châteaux, …).
3. Outputs landed in `/tmp/region_names_out/<country>.txt` as
   `<region_id>|<new_name>` lines.
4. `tools/apply_region_names.py` aggregated those into
   `tools/region_name_overrides.json`.
5. A manual dedup pass cleaned up agent-induced duplicates
   (`Amalfi Coast` vs `Amalfi & Cilento` etc.). The overrides file is the
   source of truth for any further name editing.

`build_regions.py` reads `region_name_overrides.json` at the very end of
`render_outputs()` and applies it. Manual edits to that file survive
rebuilds.

### 7. Render outputs

`render_outputs()` writes:

- `static/geo/regions.geo.json` — FeatureCollection with `properties`
  containing `id`, `name`, `parent`, `n_locs`, `top` (top destination
  name). Roughly 2.6 MB.
- `static/geo/regions_data.json` — `region_id → {name, parent, n_locs,
  is_split, top_locations[]}` where each top location includes title,
  snippet, path, score, lat, lon. Roughly 800 KB.

Continent and country pages are filtered out of `top_locations` and the
`n_locs` count.

## Frontend (regions_app/templates/regions_app/map.html)

One file, plain Leaflet + a single async IIFE. Highlights:

- Loads both geo files with `Promise.all`, then `L.geoJSON(...).addTo(map)`.
- Polygons render desaturated (`hsl(hue, 18%, 78%)`, opacity 0.4). When
  visited, they switch to saturated (`hsl(hue, 65%, 50%)`, opacity 0.75).
  Hue is deterministic from the parent country name so adjacent regions in
  the same country share a colour family.
- Click → opens the side panel with the region name, n_locs, a "visited?"
  checkbox, and the top 5 destinations (each clickable to the World66
  location page). Single click does **not** fitBounds — just panel.
- Double-click → toggles visited without opening the panel.
- Visited state stored in `localStorage` under `world66.visited`. Counter
  shown at the top of the panel.
- Top-nav search input is hijacked (clone-and-replace to drop the
  base.html listeners that would fetch `/api/search`) and instead filters
  the 440 region names + parents inline. Clicking a search result calls
  `selectRegion(id)`.
- `bindTooltip` is *not* used — Leaflet 1.9.4 has a known crash in
  `_setAriaDescribedByOnLayer` on some MultiPolygon geometries.
- A `/regions` → `/regions/` redirect lives in `world66/urls.py` because
  the guide's catchall route otherwise tries to serve `regions` as a
  content page.

## Tuning knobs (all in `tools/build_regions.py`)

| Knob | Default | Effect |
|---|---|---|
| `IMPORTANCE_K` | 4.0 | How steeply top destinations dominate. K=4 makes score 1.0 worth 100× score 0.5. |
| `BUDGET` | 6000 | Max importance per region before subdivision. Lower = more splits. |
| `MAX_SPLITS_PER_SUBUNIT` | 25 | Hard cap so one giant country doesn't explode. |
| `TOP_LOCATIONS_PER_REGION` | 5 | How many destinations the panel shows. |

## How to rebuild

```bash
source venv/bin/activate
python tools/build_regions.py            # rebuilds regions.geo.json + data.json
# (or, after editing tools/region_name_overrides.json directly, just re-run
#  the same — overrides are applied at the end of render_outputs.)
```

To re-run the naming agents from scratch (e.g. after lowering BUDGET):

1. Rebuild without overrides to get the raw cells.
2. Regenerate `/tmp/regions_to_name.json` filtered to `is_split: True`.
3. Launch one agent per country (`Agent` tool, see commit history for the
   prompt template).
4. Each agent writes `/tmp/region_names_out/<country>.txt`.
5. `python tools/apply_region_names.py` ingests into the overrides file.
6. `python tools/build_regions.py` to apply.

## Known issues / future work

- **China is under-represented**: only ~70 indexed Chinese cities (vs. 49
  for Thailand, 55 for Japan in much smaller areas), and the top Chinese
  city scores 0.80 vs. 0.93 in Vietnam, 0.97 in Japan. China gets only 3
  Voronoi cells where it should have ~10. Root cause is data, not the
  pipeline: gaps include Huangshan, Zhangjiajie, Dunhuang, the Great Wall
  sections, Mount Tai, Pingyao, Yunnan rice terraces, the Silk Road, etc.
  Same applies to a lesser degree to Africa and Central Asia.
- **Lowering BUDGET would require re-running the agent naming pass** —
  new cells appear and the overrides file would be incomplete. The
  pipeline supports it, just budget the agent calls.
- **Visited state is per-browser via localStorage.** If we want
  cross-device persistence, sync into `passport_app`'s session-cookie
  store (or migrate to a proper account model).
- **A handful of agent-named cells share words with their neighbours**
  ("Northern California" vs "Southern California" — intentional;
  "French Alps" vs "Nice & Southern Alps" — borderline). A scan for
  shared significant words is at the end of the dup-fix conversation in
  the git log; the dedup pass already swept the worst offenders.
- **Server-side scoring**: regions could be served via a Django view
  instead of static files, but the current setup is plenty fast and
  cache-friendly.

---

# Background notes for a future blog post

The technical sections above describe **what** the system does. The notes
below capture **why** we built it this way, what didn't work, and the
surprises along the road. Saving this here so a blog post is mostly a
matter of rearranging and adding screenshots.

## Why not just colour countries?

Every "visited countries" map looks the same: a flat 195-country
choropleth. It rewards box-ticking — fly into the capital, stamp the
passport, claim the country. It also wildly distorts what "visiting" means.
Russia is one box. Vatican City is one box. Someone who has been to Berlin,
Paris and Tokyo "fills" three boxes; someone who has driven from San
Francisco to Maine fills *one*.

The goal here was to make a map whose units are roughly travel-comparable.
Going to Tuscany feels like "a thing you did"; so does going to the
Cinque Terre; so does going to Sicily — they belong on the same map at
the same level of granularity, even though they're all in Italy.

That ruled out admin boundaries (states, provinces) because they're too
uniform — Tuscany, Vermont, and Tasmania are at very different "travel
scales" despite each being a single admin unit. It ruled out a fixed grid
(hexbin etc.) because populated areas should split into more cells than
empty ones. It pointed at a Voronoi tessellation weighted by some measure
of touristic importance.

## What "importance" means here

World66 already has a per-location score from a separate ranking pipeline
(`tools/rank_locations.py` — Plackett-Luce MLE on Claude-judged
ranking matches). The raw score is in [0,1] but the interesting range is
narrow — 0.3 to 0.8 covers almost everything. To make Paris dominate a
village by 100×, scores get an exponential transform:

```python
importance = 10 ** (score * 4)
```

K=4 makes a score-1.0 destination worth 100× a score-0.5 one. The K was
tuned by eye on the resulting cell distribution.

## Why Natural Earth subunits, not countries

Plain country polygons fold overseas territories into their sovereign:
Greenland disappears into Denmark, Hawaii into the USA, Réunion and French
Guiana into France. For a "places I've visited" map that's terrible —
visiting Greenland is obviously a different experience from visiting
Copenhagen, and you want to be able to mark it separately.

Natural Earth's "admin 0 — map subunits" layer fixes this: France splits
into mainland + Corsica + each overseas department; the UK splits into
England/Scotland/Wales/N. Ireland + every Crown dependency + every
British Overseas Territory; the US has Alaska, Hawaii, PR, Guam, USVI,
American Samoa, Northern Mariana Islands as separate polygons; the
Netherlands has Aruba, Curaçao, Sint Maarten, Caribbean Netherlands.

For dense single-sovereign areas (mainland France, mainland US, mainland
Italy, …) we still need to subdivide — that's where the Voronoi splits
come in. Subunits are the *floor*: we never cross them.

## What didn't work (and how we noticed)

The first version used the obvious approach: take the top-N cities of
each subunit by importance, use them as Voronoi seeds, clip to the
subunit polygon. The trouble showed up immediately:

- **Hamburg ended up inside Rothenburg ob der Tauber's cell.** Northern
  Germany has no "tourist hotspot" comparable to Munich, Heidelberg, or
  the Romantic Road — so no seed sits up there. Every northern German
  town then snaps to whichever southern seed is geographically closest.
  Rothenburg won the contest. Visually: a region named after a tiny
  medieval town contained Germany's second-largest city.

- **Berlin landed inside Dresden's cell.** Same dynamic, plus a
  data-quality bug we hadn't realised existed: the page
  `content/europe/germany/berlin.md` was tagged `loc_type: region`
  rather than `city`, so our seeding code (which filtered to cities)
  silently dropped Berlin from the candidate pool. The Dresden cell
  inherited Berlin geographically because Dresden was the closest seed.

That second one was the kicker. It pointed at an *algorithmic* miss in
the original `loc_type` classification — the Phase 1 script
(`tools/set_loc_type.py`) had used the heuristic "a page with children
is a region, a leaf is a city". Berlin has sub-pages (its
neighbourhoods), so it got labelled as a region. So did 65 other big
cities. An audit (run by 5 parallel subagents over all 640
`loc_type: region` pages) found them all; a second pass over their 91
location-children sorted out which children were truly Berlin
neighbourhoods (flip to `type: neighbourhood`), which were satellite
towns wrongly nested (promote out — Pasadena out of LA, Santa Monica
out of LA, Burnaby out of Vancouver, Skerries out of Dublin, …), and
which were stubs worth deleting. That's PR #965, parallel and
unblocking on this one.

## What we switched to

Three changes, each fixing a class of failure:

1. **Importance-weighted k-means picks the centroids**, not "top-N
   cities". Lloyd's iterations move each centroid to the
   importance-weighted mean of its assigned locations. Centroids drift
   toward city *density*, not tourist *hotspots*. Northern Germany now
   gets a centroid because there are real cities up there even if none
   of them individually beats Munich. Hamburg becomes the centre of its
   own cell — exactly what you want.

2. **Voronoi over every location, then merge by label.** The naïve
   approach makes K-cell Voronoi cells with straight cell-to-cell
   borders. Visually it screams "computer". Instead we tessellate the
   subunit using all of its location points, label each cell by which
   centroid its seed is closest to, and `shapely.ops.unary_union` the
   cells that share a label. The result: jagged organic borders that
   track real city density between regions, not arbitrary straight
   lines.

3. **Names come from a per-country LLM agent**, not the top-scoring
   city. Naming a cell after its top destination gave us regions called
   "Key West" (covering most of Florida), "Riomaggiore" (Cinque Terre),
   "Reims" (Champagne wine country) — accurate but useless. We launched
   47 subagents, one per multi-cell country, each given the cells +
   their top destinations and asked for short, evocative names. The
   agents picked real cultural/geographic names where they existed
   (Tuscany, Provence, Cinque Terre, Champagne, Florida Keys, Rocky
   Mountains, U.S. Southwest, Bavaria) and reached for sensible
   directional names where they didn't (Northern Germany, Eastern
   China, Upper / Lower Nile).

## The data-quality reveal

Building this exposed two data problems we had no idea were there.

- **The Berlin tagging bug** (above), plus 65 of its peers.
- **China is dramatically under-represented.** China has 70 indexed
  cities to Japan's 55 and Thailand's 49 — for a country with that much
  surface area, tourism, and cultural variety, the count should be in
  the hundreds. The *scores* are also flat: China's top city (Hong Kong,
  0.80) ranks below Vietnam's (Ha Long Bay, 0.93) and Japan's (Kyoto,
  0.97). The Voronoi machinery exposed this neatly — China got only
  three cells because its total importance budget is low. Same applies
  to a lesser degree to large parts of Africa and Central Asia.

This is the kind of thing you only see when you map your data; the gap
is invisible when you're reading it ranked alphabetically.

## How the LLM naming actually worked

It's tempting to think of "ask an LLM to name a region" as something
that should be uniform and automatic. In practice the structure
mattered. Per-country agents (rather than one big batch) made the names
*consistent within a country* — France's cells came back as Provence,
French Riviera, Loire Châteaux, French Alps, Champagne, Burgundy,
Alsace — coherent because the same agent picked all 13. A single global
agent would have drifted.

We launched 47 agents in parallel (across three waves of ~10–20 each
to dodge rate limits). The prompt was tight: country name, the cell
list with top destinations, a small set of guidelines (prefer real
cultural/geographic names; use "X and around" when one city dominates;
avoid the smallest town; don't repeat the parent country). Output went
to per-country text files which a small Python script aggregated into
the persistent overrides file.

The result was good but not perfect. A handful of within-country
duplicates slipped through ("Amalfi Coast" vs "Amalfi & Cilento" in
Italy, "Loire Châteaux" vs "Loire Valley & Normandy" in France). A
scan-and-fix pass cleaned them in a few minutes.

## By the numbers

```
6,642 scored locations with coordinates (the seed input)
  308 Natural Earth subunits (the polygon floor)
  440 regions total
  260   - whole subunits (kept as Natural Earth named them)
  180   - split cells (Voronoi-tessellated mainland of large subunits)
   47 countries that needed splitting
    1.3M total world importance (sum of importance over all locations)
  6000  - per-region importance budget before subdivision
   12 within-country name duplicates fixed by hand after the agent pass
   66 mis-tagged "regions" promoted to cities (PR #965 dependency)
   91 of their children triaged: 9 -> neighbourhood, 10 -> deleted,
                                  72 -> promoted out
    4 POIs found that needed neighbourhood tags after the retag
```

## Lessons / takeaways

1. **Voronoi seeded by k-means weighted means is a better default**
   than top-N nominees for any task where the underlying point cloud
   isn't uniform. Top-N seeds cluster where individual points are
   loud; k-means seeds cluster where mass is.

2. **Merging Voronoi cells via `unary_union` is a cheap way to get
   organic-looking partitions** that respect underlying density. The
   resulting boundary geometry is jagged at a scale that matches the
   point spacing — feels right visually.

3. **Per-country LLM naming with full local context outperforms
   global naming.** The model can be consistent across one country's
   cells if it sees all of them in one prompt; it can't if it sees
   them in isolation. The total token budget barely changes.

4. **Mapping your data finds bugs you'd never see ranked.** The
   `loc_type: region` heuristic miss for 66 cities only became obvious
   when those cities started showing up wrongly inside Voronoi cells
   on a world map. Same for China's under-coverage.

5. **Overrides files want to be the source of truth, not derived.**
   The first version of the naming pipeline re-read `/tmp` files on
   every build and regenerated the overrides. Manual edits got
   clobbered. Moving the curated names into a real file (committed
   to the repo) and applying them as the last step of the build made
   the editing flow safe.

6. **"What's a region?" is a UI question, not a data question.** Once
   we accepted that the unit didn't need to match a real
   administrative boundary, every other design problem got easier.

## Suggested blog-post outline

A draft skeleton, mapping the technical material above into a narrative
arc:

1. **Hook** — "Visited countries maps lie. Here's what a better one
   looks like." Screenshot of the final map with a few regions
   coloured saturated.
2. **What's wrong with country-level** — Russia vs Vatican City; the
   "I've been to France because I had a layover" problem; the
   incentive to box-tick.
3. **What I want instead** — units that feel travel-comparable;
   organic boundaries; visited toggle; click-through to destinations.
4. **First attempt: Voronoi from top cities** — what it gets right
   (overseas territories handled via Natural Earth subunits),
   what it gets wrong (Hamburg in Rothenburg's cell). Screenshot
   of the bad version.
5. **The data-quality detour** — Berlin tagged as a region;
   discovering 66 mis-classified cities; a parallel PR to fix
   them. Short, optional aside.
6. **Importance-weighted k-means** — what it is, why it produces
   better seeds. Show before/after of Germany.
7. **Organic borders via cell merging** — the Voronoi-of-locations +
   `unary_union` trick. Show before/after of borders.
8. **Naming with subagents** — the failure mode of top-city names
   ("Key West" for Florida); per-country agents; the agreement
   problem (duplicates), the dedup pass.
9. **What it revealed** — China is under-represented; broader
   data-quality lessons.
10. **Try it** — link to the live page; localStorage persistence;
    suggestions to extend (server-side passport sync, more
    regions for under-covered areas).

Visuals to capture before posting:

- World map at default zoom, all regions desaturated
- Same map with a personal "visited" pattern lit up
- Side-panel screenshot with a region selected and its top
  destinations
- Germany regions before/after the k-means switch (Hamburg's cell)
- Generic Voronoi straight borders vs. our organic ones (zoom on
  any large country)
- The China gap — wide cells with thin coverage

