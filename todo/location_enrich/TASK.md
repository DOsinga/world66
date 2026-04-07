# Location Enrich Task

Add new content to locations that have already been cleaned up (see `location_cleanup`). This task assumes the location already has the right section structure — if it still has `sights/` or junk sections, run cleanup first.

## For each location

1. **Read** the existing location file and all section/POI files to understand what's already there

2. **Add books section** per LOCATIONS.md:
   - 3–5 novels or literature that illuminate the city
   - Each book is a POI in `books/` with `author:` and optionally `isbn:`

3. **Add `story:` fields** to 3–5 major sights in `things_to_do/`:
   - Specific, surprising, concise (2–4 sentences)
   - Only add stories you know are accurate

4. **Add neighbourhood POIs** for large cities:
   - 3–5 characterful districts as `Neighbourhood` category POIs in `things_to_do/`
   - Tag relevant POIs in other sections with `neighbourhood: "Name"`

5. **Create missing sections** where they add value:
   - `when_to_go.md`, `getting_there.md`, `getting_around.md` if absent
   - `shopping.md`, `beaches.md`, `day_trips.md` where relevant

6. **Fill gaps in existing sections**:
   - If a well-known attraction is missing from `things_to_do/`, add it
   - If `eating_out/` or `bars_and_cafes/` is thin, add notable places

7. **Add hero image** — if the location file has no `image:` field, use the `find-photo` skill to find and assign one.

8. **Commit** as "Enrich: City Name" — one commit per location

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. Research destinations using web search — don't invent details.

## Batch files

Each file contains ~5 locations. Process all in a batch, commit each separately.
