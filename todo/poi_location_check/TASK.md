# POI Location Check Task

Verify the coordinates of every POI using Nominatim. This is a focused task: coordinates only. Do not rewrite content, do not add snippets, do not delete spam — just get the locations right.

Use **5 agents** per batch, dividing the batch roughly equally between them.

## For each POI in the batch

### 1. Determine expected location

Derive the city/country from the file path:
- `content/europe/france/paris/le_louvre.md` → Paris, France

The POI's `title` field is the name you'll look up.

### 2. Check Nominatim

Query Nominatim to find the POI's real coordinates:

```
GET https://nominatim.openstreetmap.org/search
  ?q=<title>, <city>, <country>
  &format=json
  &limit=3
  &addressdetails=1
User-Agent: world66-poi-checker/1.0
```

- Always include `User-Agent: world66-poi-checker/1.0` in the request header.
- Wait at least 1 second between Nominatim requests (rate limit).
- Try the most specific query first (`title, city, country`). If no result, broaden to (`title, country`) or just (`title, city`).
- Pick the result whose `display_name` or `address` best matches the expected location — ignore results from the wrong country.
- If Nominatim returns nothing useful, use a web search to find coordinates.

### 3. Compare with stored coordinates

**If the POI has `latitude` / `longitude`:**

Calculate the distance between the stored point and the Nominatim point:
- Within ~500 m: **no change needed**.
- Between 500 m and 5 km: check whether the discrepancy is explainable (large complex, neighbourhood centroid). If it looks like a genuine error, update to the Nominatim coordinates.
- More than 5 km apart: almost certainly wrong. Update to the Nominatim coordinates.
- If Nominatim returned coordinates in a clearly wrong country, do **not** blindly update — investigate with a web search and use your best judgement.

**If the POI has no `latitude` / `longitude`:**

Add the coordinates returned by Nominatim (or your web search result) to the frontmatter.

### 4. Write the fix

If a coordinate change is needed, update the file's frontmatter using `python-frontmatter`. Only touch `latitude` and `longitude` — do not alter any other field.

Example of the fix pattern (Python):

```python
import frontmatter

post = frontmatter.load(path)
post['latitude'] = round(lat, 6)
post['longitude'] = round(lon, 6)
with open(path, 'wb') as f:
    frontmatter.dump(post, f)
```

Round to 6 decimal places (~10 cm precision — more than enough).

### 5. Skip gracefully when uncertain

If you cannot confidently determine the correct coordinates (ambiguous name, no Nominatim hit, can't tell which city), leave the file unchanged. Do **not** guess. It is better to leave a coordinate blank than to put in wrong ones.

## Tips

- The path encodes the country and city — use it as the primary location context.
- Nominatim works well for named landmarks, museums, parks, and restaurants in major cities. It is less reliable for small local businesses or obscure sites.
- Old World66 data has frequent off-by-continent errors: a London pub with coordinates in Texas, a Tokyo shrine with coordinates in California. These are obvious in the distance check.
- For a restaurant/bar where Nominatim can't find the exact place, the parent city centroid is acceptable as a fallback if no better coordinates are available.
