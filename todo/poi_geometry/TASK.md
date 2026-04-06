# POI Geometry Task

Fetch and store OSM geometry (coordinates of ways) for Street, Square, and Park POIs
so the map can render them as lines/polygons instead of just a dot.

## What this does

POIs with `category: Street`, `category: Square`, or `category: Park` have a lat/lng
coordinate but the map currently shows just a circle marker at that point. With stored
geometry we can draw the actual shape of the street or park on the map.

The geometry is stored in the POI's frontmatter as a `geometry` field — a list of
`[lat, lon]` pairs. The rendering side reads this and draws a polyline or polygon.

## How to run

For each city in a batch file, run:

```bash
python3 tools/fetch_osm_geometry.py <city_path>
```

For example:
```bash
python3 tools/fetch_osm_geometry.py europe/netherlands/amsterdam
```

The script will:
1. Find all POIs under `content/<city_path>/` with category Street/Square/Park
   that have lat/lng but no `geometry` yet
2. Query the Overpass API for each (1 req/sec, respects usage policy)
3. Write the geometry back into the frontmatter

## After running

Review the changes with `git diff` — spot-check a few POIs to make sure the geometry
looks reasonable (right street, right shape). Some may have no match (e.g. very short
alleys not in OSM) — that's fine, they'll keep showing as a dot.

Commit as: `Geometry: <City Name>`

## Batch files

Each batch file contains one city path per line. Process all cities in the batch,
one commit per city.

## Rendering

Once geometry is stored, a future PR will update `world66map.js` and `views.py`
to read the `geometry` field from the page meta and draw it on the map.
The geometry will be passed as a separate `geometry_json` template variable
(similar to `markers_json`).
