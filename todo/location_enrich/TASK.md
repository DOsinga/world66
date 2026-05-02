# Location Enrich Task

Add new content to locations that have already been cleaned up (see `location_cleanup`). This task assumes the location already has the right section structure — if it still has `sights/` or junk sections, run cleanup first.

## For each location

1. **Read** the existing location file and all section/POI files to understand what's already there.

2. **Determine the city tier** — check whether the location has a `city_tier` field. If not, assign one based on the tier table in LOCATIONS.md and add it to the frontmatter. Also add city-level `tags` (e.g. `[culture, museums, skiing]`) if missing. The tier drives everything that follows.

3. **Calibrate the work** — use the tier to set your targets before writing anything:

   | Tier | things_to_do | eating_out | bars_and_cafes | shopping |
   |------|-------------|------------|----------------|----------|
   | 1 | 25–50 POIs | 10–25 POIs | 10–25 POIs | 5–15 POIs |
   | 2 | 5–10 POIs | writeup only (POIs only if genuinely standout) | writeup only (POIs only if genuinely standout) | writeup only |
   | 3 | writeup only | writeup only | writeup only | writeup only |
   | — | overview only | — | — | — |

   Tier 1 eating_out POIs: landmark restaurants, places famous for a local dish, food markets, streets or squares with diverse options.
   Tier 1 bars_and_cafes POIs: iconic cafes, bars with local identity, clubs with a reputation, local specialties (jazz clubs, karaoke bars), streets lined with bars.
   Tier 1 shopping POIs: only major shops that are sights in themselves, historic arcades, famous markets, major shopping streets.

4. **Add books section** per LOCATIONS.md:
   - 3–5 novels or literature that illuminate the city
   - Each book is a POI in `books/` with `author:` and optionally `isbn:`
   - Skip for Tier 3 and unclassified

5. **Add `story:` fields** to major sights in `things_to_do/`:
   - Specific, surprising, concise (2–4 sentences)
   - Only add stories you know are accurate
   - Aim for 3–5 stories on Tier 1 cities, 1–2 on Tier 2

6. **Add neighbourhood POIs** for Tier 1 cities:
   - 3–5 characterful districts as POIs with `tags: [things_to_do, neighbourhood]`
   - Tag relevant POIs with the neighbourhood slug (e.g. `tags: [eating_out, de_pijp]`)

7. **Create missing sections** appropriate to the tier:
   - Tier 1: `when_to_go.md`, `getting_there.md`, `getting_around.md`, `day_trips.md` (use `linked_locations:`), `beaches.md` if coastal
   - Tier 2: `when_to_go.md`, `getting_there.md`, `getting_around.md`, `beaches.md` if coastal
   - Tier 3: `getting_there.md` if useful

8. **Fill gaps in existing sections** up to the tier targets:
   - If a well-known attraction is missing from `things_to_do/`, add it
   - Add eating_out and bars_and_cafes POIs to reach the Tier 1 targets if they fall short

9. **Add hero image** — if the location file has no `image` field, use the `find-photo` skill to find and assign one.

10. **Commit** as "Enrich: City Name" — one commit per location

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. Research destinations using web search — don't invent details.

## Do not invent

**Never fabricate a POI.** Every restaurant, bar, cafe, shop, or attraction you add must be a real, verifiable place. Use web search to confirm it exists before writing it up. If you cannot verify a place exists, do not add it — a shorter list of real places is far better than a longer list with invented ones. This applies equally to names, addresses, and descriptions: do not guess at details you are not certain of.

## Batch files

Each file contains ~5 locations. Process all in a batch, commit each separately.
