# Location Create Task

Add a new world66 location page for a city that doesn't yet have one.

## Input format

Each batch file is NDJSON — one city per line. Each record has:

- `name`, `country_id`, `coordinates {latitude, longitude}`, `snippet` — city-level identity
- `score` — a popularity number, ignore for placement
- `attribution[]` — Wikipedia / Wikivoyage / OSM URLs for the city
- `pois[]` — candidate points of interest, each with `name`, `coordinates`, `tag_labels[]`, `snippet`, and an `image{}` block when available

The `snippet` and `pois` fields are **candidates and reference data, not content to copy**. The traveler-facing prose has to be written in world66's voice (see STYLE.md), and POI coordinates should still be re-verified.

## For each item

1. **Confirm the city is genuinely missing.**
   - Try `find content -iname '<slug>.md'` with the obvious slug + diacritic-folded variants. Read CLAUDE.md, STYLE.md, LOCATIONS.md, and the relevant CONTINENTS.md / COUNTRIES.md before placing.
   - If a file shows up, verify by coordinates — sometimes two cities share a name.
   - If it actually exists, mark it done via `python3 tools/mark_done.py location_create <path>` and skip.

2. **Find the right place in the tree.**
   - Look at how neighbouring cities in the same country are placed. Italian Sicilian towns live under `europe/italy/sicily/...`; French Brittany cities live directly under `europe/france/...`. **Match the existing pattern. Don't invent a new layer.**
   - For US cities, place under `northamerica/unitedstates/<state>/<slug>.md`.

3. **Pick the slug.** Lowercase, no spaces, no hyphens, single word. Strip diacritics. Match the convention of existing siblings (e.g. `miamibeach`, `tomar`, `jerezdelafrontera`).

4. **Verify coordinates** with `python3 tools/wiki_geosearch.py <lat> <lng> --radius 5000 --limit 25 --json`. Use the result to confirm the city is where the JSON says it is, and to pull POI candidates with their lat/lon.

5. **Write the main location file** at `content/<path>/<slug>.md`:
   - Frontmatter: `title:`, `type: location`, `loc_type: city` (or `feature` for natural sites, `region` for areas), `latitude:`, `longitude:`.
   - Body: a **2–4 paragraph overview** in world66's voice. Practical, opinionated, concise. **Do not copy from Wikipedia, Wikivoyage, Atlas Obscura, or the Triposo `snippet`** — write the prose from your own knowledge of the place.
   - After step 8, return to the overview and add markdown links to the major POIs you've created.

6. **Decide the POI target**:
   - Capital / major destination: at least 50 POIs
   - Medium importance (well-known city, common stop): around 15
   - Smaller place: the real highlights only, however many that is

7. **Pick POI candidates** from three sources — don't skip any:
   - The Triposo `pois[]` in the batch line. Treat `tag_labels`, `coordinates`, and the `image{}` block as data; treat the `snippet` as a hint about what the place is. Don't copy snippet text.
   - `python3 tools/wiki_geosearch.py <lat> <lng> --radius 5000 --limit 25 --json` — Wikipedia-tagged places with verified coordinates.
   - `python3 tools/grep_obscura.py <country> <city>` — Atlas Obscura entries **for inspiration only**. Do not copy or paraphrase Atlas Obscura prose.

   Cross-reference the three lists. Drop duplicates and the long tail of generic restaurants/shops. Aim for the POI mix world66 expects: anchor sights, neighbourhoods, eating_out, bars_and_cafes.

8. **Write POI files** at `content/<path>/<slug>/<poi_slug>.md` — flat, as siblings of section files:
   - Each POI: at least two paragraphs of body text; longer for major sights. Written from your own knowledge — not Triposo, not Wikipedia paste.
   - `tags:` includes the section tag (`things_to_do`, `eating_out`, `bars_and_cafes`, etc.) and category tags (`sight`, `museum`, `restaurant`, …).
   - `latitude` and `longitude` set — **from `wiki_geosearch --json` when the place appears there**, or from the Triposo POI record when you trust it. If neither has it, look up OSM or skip the POI. Do not invent coordinates.
   - For major sights with the `things_to_do` tag, add a `story:` field — 2–4 sentences, specific, surprising, accurate.

9. **Add neighbourhood POIs** for large cities:
   - 3–5 characterful districts as POIs with `type: neighbourhood` and `tags: [things_to_do, neighbourhood]`.
   - Tag POIs that sit in that district with the neighbourhood slug.

10. **Create sections** where they add real value (don't make stubs):
    - `when_to_go.md`, `getting_there.md`, `getting_around.md` for any covered city
    - `shopping.md`, `beaches.md`, `day_trips.md`, `books.md` where relevant
    - Skip any section that would be a placeholder — LOCATIONS.md prefers no section over a stub.

11. **Add a hero image — both the file AND the frontmatter.** Use `tools/find_photo.py`:
    ```
    python3 tools/find_photo.py --no-classify <content-path>
    ```
    The path is `/europe/switzerland/lucerne` (leading slash, no `content/` prefix, no `.md`). The script prints candidate thumbnails as JSON. Pick the best by reading the thumbnail files (`thumb_path` field) and judging by relevance to the place and visual quality. Then:
    ```
    python3 tools/find_photo.py --select-meta '<json-of-chosen-candidate>' <content-path>
    ```
    This **downloads the full image, resizes it, saves it next to the `.md`, AND writes the `image:`/`image_source:`/`image_license:`/`image_attribution:` frontmatter fields.** All in one call. The local image filename will be the slug (e.g. `lucerne.jpg`).

    Do NOT manually write the `image:` frontmatter and skip the download — that leaves a broken reference. The image file must exist on disk next to the `.md`.

    If `find_photo.py` finds no suitable candidate (exit code 1, empty `candidates` array), leave the hero image off entirely. Don't fabricate sources.

12. **Add internal links from the overview.** Re-read the overview and add markdown links wherever a POI name is mentioned, e.g. `[Saint Ursus Cathedral](/europe/switzerland/solothurn/saint_ursus_cathedral)`. The overview is the only page with no built-in path to individual POIs.

13. **Mark done:**
    `python3 tools/mark_done.py location_create <path/to/main.md>`

14. **Commit** as `Create: <City Name>` — one commit per location.

## Before committing each city

Run this checklist:

- [ ] Main location file written in world66's voice (not a Wikipedia / Triposo paste)
- [ ] POI count is at or near the target for the city's importance tier
- [ ] `python3 tools/wiki_geosearch.py` was run and its coordinates used
- [ ] `python3 tools/grep_obscura.py` was run; obscura matches are inspiration only
- [ ] Each new POI has coordinates that match its actual location
- [ ] Major `things_to_do` POIs have a `story:` field
- [ ] Hero image: the actual `.jpg` file exists next to the `.md` AND the frontmatter has `image:`/`image_source:`/`image_license:` (use `tools/find_photo.py` — don't write the frontmatter without saving the file)
- [ ] Sections created only where they add real content
- [ ] Overview text contains markdown links to the major POIs
- [ ] `done: { location_create: <today> }` set on the main location file

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. **Research destinations — do not invent details.** Where uncertain, omit.
