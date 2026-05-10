# Location Enrich Task

Add new content to locations that have already been cleaned up (see `location_cleanup`). This task assumes the location already has the right section structure — if it still has `sights/` or junk sections, run cleanup first.

## Prerequisites

Before processing a location, verify its frontmatter contains `done: location_cleanup`. If it doesn't, skip it — cleanup must happen first.

## For each location

1. **Read** the existing location file and all section/POI files to understand what's already there.

2. **Add books section** per LOCATIONS.md — if `books/` doesn't already exist:
   - 3–5 novels or literature that illuminate the city (not travel guides or history books)
   - Each book is a POI in `books/` with `author:` and optionally `isbn:`
   - Use web search to verify the books are real and well-regarded

3. **Add `story:` fields** to 3–5 major sights in `things_to_do/`:
   - Specific, surprising, concise (2–4 sentences)
   - Use web search to verify each anecdote is accurate — do not invent or guess
   - See LOCATIONS.md for the exact format

4. **Add neighbourhood POIs** for cities large enough to have distinct districts:
   - 3–5 characterful districts as POIs with `tags: [things_to_do, neighbourhood]`
   - Tag relevant existing POIs with the neighbourhood slug (e.g. `tags: [eating_out, de_pijp]`)
   - See LOCATIONS.md for tag rules

5. **Create missing sections** where they genuinely add value:
   - `when_to_go.md`, `getting_there.md`, `getting_around.md` if absent and the city warrants them
   - `shopping.md`, `beaches.md`, `day_trips.md` where relevant
   - Don't create stub sections — only create one if you can write real content

6. **Fill gaps in existing sections**:
   - If a well-known attraction is missing from `things_to_do/`, add it with coordinates
   - If `eating_out/` or `bars_and_cafes/` is thin, add notable places
   - Every POI must have `latitude` and `longitude` — do not add a POI without them

7. **Add hero image** — if the location file has no `image` field, use the `find-photo` skill to find and assign one.

8. **Mark done** — add `location_enrich: 'YYYY-MM-DD'` under the `done:` key in the location's frontmatter.

9. **Commit** as `"Enrich: City Name"` — one commit per location.

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. Always use web search to research — never invent details.

## Reference implementations

See LOCATIONS.md for reference cities (Rome, Florence, Milan, etc.) that demonstrate the expected structure.

## Batch files

Each file contains ~5 locations. Process all in a batch, commit each separately.
