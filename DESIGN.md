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
