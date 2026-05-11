# Location Enrich Task

## For each location

1. **Read** the existing location file and all section/POI files to understand what's already there

2. **Spam**
   Scan the location for spam and bad structure. make sure that all the tags are in order, there's no
   nonsense going on.

3. **Fill out pois**
   Important cities should have at least 50 pois. Mediumly important ones around 15 and even the smaller ones should
   have some highlights. Use the tools/wiki_geosearch.py to fetch candidates from the wikipedia. Check the obscura
   folder for inspiration on off the beaten track pois. Use your own knowledge or do a search to get to the number
   of pois required.

3. **Pois**
   For each poi, make sure the description is long enough. Typically you want to have two paragraphs of description
   at least, longer for things that are of true importance to travellers. Also make sure the pois have the right
   tags. Check the coordinates using osm or search or against the wikisearch from the previous step

3. **Add `story:` fields** to major sights with the `things_to_do` tag
   - Specific, surprising, concise (2–4 sentences)
   - Only add stories you know are accurate

4. **Add neighbourhood POIs** for large cities:
   - 3–5 characterful districts as POIs with `tags: [things_to_do, neighbourhood]`
   - Tag relevant POIs with the neighbourhood slug (e.g. `tags: [eating_out, de_pijp]`)

5. **Create missing sections** where they add value:
   - `when_to_go.md`, `getting_there.md`, `getting_around.md` if absent
   - `shopping.md`, `beaches.md`, `day_trips.md` where relevant

6. **Fill gaps in existing sections**:
   - If a well-known attraction is missing from `things_to_do/`, add it
   - If `eating_out/` or `bars_and_cafes/` is thin, add notable places

7. **Add hero image** — if the location file has no `image` field, use the `find-photo` skill to find and assign one.

8. **Commit** as "Enrich: City Name" — one commit per location

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. Research destinations using web search — don't invent details.
