---
name: find-wikipedia-pois
description: search Wikipedia for geotagged articles near a location and create POIs from the results. invoke when the user wants to find new points of interest for a city using Wikipedia
argument-hint: <content-path, e.g. europe/italy/lazio/rome>
---

Search Wikipedia for geotagged articles near a World66 location and interactively review them as potential POIs.

## Steps

### 1. Determine the location

If no argument is provided, ask the user which city they want to search. Resolve the content path and read the location's `.md` file to get its `latitude` and `longitude`.

### 2. Run the geosearch

Use `tools/wiki_geosearch.py` to find Wikipedia articles near the location. Search multiple points across the city to get good coverage:

```bash
python3 tools/wiki_geosearch.py LAT LNG --radius 10000 --json
```

For larger cities, search multiple centre points (downtown, major neighbourhoods) and deduplicate by `pageid`. The API returns max 50 results per query, so multiple queries from different points gives better coverage.

### 3. Filter results

Remove results that are not travel-relevant:
- Transit stations, bus stops, rail lines
- Residential buildings, condos, apartment complexes, office towers
- Schools, hospitals, fire stations, police departments
- Courts, government offices, detention centres
- Census-designated places, unincorporated areas
- Generic neighbourhood/district articles that duplicate what we already cover

Also remove any POIs the city already has (compare against existing `.md` files in the city's content directory).

### 4. Present candidates to the user

Show the filtered list grouped by likely category (museums, architecture, sights, restaurants, etc.). For each candidate show:
- Title
- Distance from city centre
- First sentence from Wikipedia
- Suggested category tag

Let the user review and select which ones to add. Go through them one by one or let the user pick from the list.

### 5. Create POI files

For each selected candidate:

1. **Fetch the Wikipedia article** using WebFetch to get enough detail to write a good POI description
2. **Use the coordinates returned by the geosearch tool** — do NOT make up or estimate coordinates. The geosearch results include `lat` and `lon` fields; use those values rounded to 4 decimal places
3. **Write the POI file** following LOCATIONS.md guidelines:
   - Use proper tags: section tag (`things_to_do`, `eating_out`, etc.), neighbourhood slug if applicable, category tag (`museum`, `sight`, `architecture`, etc.), and descriptive tags
   - Set `neighbourhood:` frontmatter for display if the POI is within a known neighbourhood
   - Add a `story:` field if you find a good anecdote in the Wikipedia article
   - Write the description in World66 style (see STYLE.md) — not a Wikipedia summary, but a travel-guide perspective on why someone should visit

### 6. Commit

Commit the new POIs with a message like `<city>: add N POIs from Wikipedia geosearch`.

## Important

- **Always use Wikipedia's coordinates.** The geosearch API returns precise lat/lon for each article. Never substitute your own guesses — they will often be hundreds of meters or even kilometres off.
- **Read LOCATIONS.md** before creating POIs, especially the tag system documentation.
- **Neighbourhood POIs** should only carry `things_to_do` + `neighbourhood` as tags. Descriptive tags go on POIs within the neighbourhood, not on the neighbourhood itself.
- **Quality over quantity.** A city with 15 well-written POIs is better than 50 stubs. Only add places that a traveller would actually want to know about.
- **Don't duplicate.** Check what POIs the city already has before adding new ones.
