# POI Location Check Task

Verify the coordinates of every POI. This is a focused task: coordinates only. Do not rewrite content, do not add snippets, do not delete spam — just get the locations right.

Use **5 agents** per batch, dividing the batch roughly equally between them.

## Guiding principle

**Trust OpenStreetMap above our own stored coordinates.** The existing lat/lon in World66 POIs is old, often wrong, and should be treated as a rough hint at best. OSM data — retrieved via Nominatim and Overpass — is the authority. When OSM says a place is somewhere, update the file to match, unless the OSM result is clearly for the wrong place (wrong country, wrong city, obviously a different venue with a similar name).

## Coordinate precision goal

We want the pin to land at the **entrance** of the place, not the centroid of a building footprint or the middle of a city block. For a restaurant, bar, or small museum this is the front door. For a large complex (palace, cathedral, airport, big museum), it is the main public entrance.

---

## For each POI in the batch

### 1. Determine expected location

Derive the city/country from the file path:
- `content/europe/france/paris/le_louvre.md` → Paris, France

The POI's `title` field is the name you will look up.

### 2. Query Nominatim

```
GET https://nominatim.openstreetmap.org/search
  ?q=<title>, <city>, <country>
  &format=json
  &limit=3
  &addressdetails=1
User-Agent: world66-poi-checker/1.0
```

- Always include `User-Agent: world66-poi-checker/1.0`.
- Wait at least 1 second between Nominatim requests (rate limit).
- Try `title, city, country` first. Broaden to `title, country` or `title, city` if no result.
- Pick the result whose `display_name` or `address` best matches the expected location — discard results from the wrong country.
- Note the returned `osm_type` (`node`, `way`, or `relation`) and `osm_id` — you need these for step 3.
- If Nominatim returns nothing useful, fall back to a web search for the coordinates.

### 3. Find the entrance (for non-trivial buildings)

Nominatim returns the **centroid** of an OSM object, which is fine for a small node (a café, a small shop) but wrong for anything with a real footprint. For POIs that are ways or relations (museums, cathedrals, palaces, parks, stadiums, airports, large markets), query Overpass for the main entrance:

**For a way:**
```
POST https://overpass-api.de/api/interpreter
data=[out:json][timeout:15];
node(w:<osm_id>)["entrance"~"^(main|yes)$"];
out body;
```

**For a relation:**
```
POST https://overpass-api.de/api/interpreter
data=[out:json][timeout:15];
node(r:<osm_id>)["entrance"~"^(main|yes)$"];
out body;
```

- Prefer `entrance=main` over `entrance=yes`. If multiple `entrance=yes` nodes exist, pick the one that faces the main street or has the most prominent position.
- If no entrance node exists in OSM (common for older data), use the Nominatim centroid — it is still better than a wrong-country coordinate.
- Small nodes (`osm_type=node`) are already a point location; skip the Overpass step entirely.

### 4. Compare with stored coordinates

Calculate the distance between the best coordinate found (entrance or centroid) and the POI's stored `latitude`/`longitude`.

| Distance | Action |
|---|---|
| < 25 m | Leave unchanged |
| 25 m – 250 m | Investigate: is the discrepancy explained by entrance vs centroid, a large complex, or a secondary entrance? Update if the new point is clearly more accurate. |
| > 250 m | Fix unconditionally. |

Off-by-continent errors are common in old World66 data (a London pub with coordinates in Texas, a Tokyo shrine in California). These are obvious — fix them.

If the POI has **no coordinates**: add what you found.

### 5. Write the fix

If a change is needed, update the file using `python-frontmatter`. Only touch `latitude` and `longitude`.

```python
import frontmatter

post = frontmatter.load(path)
post['latitude'] = round(lat, 6)
post['longitude'] = round(lon, 6)
with open(path, 'wb') as f:
    frontmatter.dump(post, f)
```

Round to 6 decimal places (~10 cm precision).

### 6. Skip gracefully when uncertain

If you cannot confidently identify the right location — ambiguous name, no Nominatim result, can't tell which city — leave the file unchanged. Do not guess. A blank coordinate is better than a wrong one.

---

## Quick reference

| POI type | Where to get coords |
|---|---|
| Small node (café, shop, statue) | Nominatim centroid |
| Named building (museum, cathedral) | Overpass entrance node, fall back to Nominatim centroid |
| Large complex / park | Overpass main entrance, fall back to Nominatim centroid |
| No Nominatim hit | Web search |
