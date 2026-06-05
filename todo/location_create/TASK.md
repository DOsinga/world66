# Location Create Task

Create new world66 location pages for cities that don't yet exist, then enrich
them with POIs and sections like an enrich pass. The cities in this task were
identified as missing-but-worth-adding via a Triposo-based gap analysis (1,800
cities scanned against the existing tree, ~123 worth-adding).

The batch file lines have the format:

```
<City Name>, <Country> [optional disambiguation in parens]
```

e.g. `Springfield, United States (Illinois)`. Use the disambiguation to pick the
right place when there are name collisions.

## For each item

1. **Confirm the city is genuinely missing.**
   - `find content -iname '<slug>.md'` with the obvious slug + diacritic-folded variants.
   - If a file shows up, verify by coordinates (sometimes there are two cities sharing a name).
   - If it actually exists: mark it `done` in its frontmatter via `python3 tools/mark_done.py location_create <path>` and move on.

2. **Find the right place in the tree.**
   - Read CLAUDE.md, STYLE.md, LOCATIONS.md, and the relevant CONTINENTS.md / COUNTRIES.md before placing.
   - Look at how neighbouring cities in the same country are placed. Italian Sicilian towns live under `europe/italy/sicily/...`; French Brittany cities live directly under `europe/france/...`. **Match the existing pattern. Don't invent a new layer.**
   - For US cities, place under `northamerica/unitedstates/<state>/<slug>.md`.

3. **Pick the slug.** Lowercase, no spaces, no hyphens, single word. Strip diacritics. Match the convention of existing siblings (e.g. `northamerica/unitedstates/florida/miamibeach`, `europe/portugal/tomar`, `europe/spain/jerezdelafrontera`).

4. **Get coordinates** for the city (Wikipedia infobox or OpenStreetMap is fine). Then run `python3 tools/wiki_geosearch.py <lat> <lng> --radius 5000 --limit 25 --json` to pull the POI candidates and their coordinates.

5. **Write the main location file** at `content/<path>/<slug>.md`:
   - Frontmatter: `title:`, `type: location`, `loc_type: city` (or `feature` for natural sites, `region` for areas), `latitude:`, `longitude:`. Add `score:` only if you have a defensible number — otherwise omit.
   - Body: a **2–4 paragraph overview** of the place in world66's voice. Practical, opinionated, concise. **Do not copy from Wikipedia, Wikivoyage, or Atlas Obscura** — write the prose from your own knowledge. After step 7, return to the overview and add markdown links to the major POIs you've created.

6. **Decide the POI target** for the city:
   - Capital / major destination: at least 50 POIs
   - Medium importance (well-known city, common stop): around 15
   - Smaller place: the real highlights only, however many that is

7. **Gather POI candidates** from all three sources — don't skip any of them:
   - `python3 tools/wiki_geosearch.py <lat> <lng> --radius 5000 --limit 25 --json` — use the `lat`/`lon` per result when writing POIs.
   - `python3 tools/grep_obscura.py <country> <city>` — Atlas Obscura entries **for inspiration only**. They tell you which places are worth covering, but **do not copy or paraphrase Atlas Obscura prose.**
   - Your own knowledge / a quick web search to fill remaining gaps to the target.

8. **Write POI files** at `content/<path>/<slug>/<poi_slug>.md` — flat, as siblings to section files, per LOCATIONS.md:
   - Each POI: at least two paragraphs of body text; longer for major sights.
   - `tags:` includes the section tag (`things_to_do`, `eating_out`, etc.) and any category tags (`sight`, `museum`, `restaurant`, …).
   - `latitude` and `longitude` set — **take them from the `wiki_geosearch --json` output** when the place appears there. If the place is not in the Wikipedia results, look it up on OpenStreetMap or skip the POI. Do not invent coordinates from memory.
   - For major sights with the `things_to_do` tag, add a `story:` field — 2–4 sentences, specific, surprising, accurate.

9. **Add neighbourhood POIs** for large cities:
   - 3–5 characterful districts as POIs with `type: neighbourhood` and `tags: [things_to_do, neighbourhood]`.
   - Tag POIs that sit in that district with the neighbourhood slug.

10. **Create sections** where they add real value (don't make stubs):
    - `when_to_go.md`, `getting_there.md`, `getting_around.md` for any covered city
    - `shopping.md`, `beaches.md`, `day_trips.md`, `books.md` where relevant
    - Skip any section that would be just a stub — LOCATIONS.md says delete-empty-section beats placeholder text.

11. **Add a hero image** for the new location:
    - Find a Wikimedia Commons image clearly of the place and clearly CC-licensed.
    - Set `image:`, `image_source:` (Commons file URL), `image_license:` (e.g. `CC BY-SA 4.0`) in the location's frontmatter.
    - Skip if you cannot confidently find one. Don't fabricate sources.

12. **Add internal links from the overview.** After all POIs exist, edit the overview to add markdown links wherever a POI name is mentioned. Example: `[Saint Ursus Cathedral](/europe/switzerland/solothurn/saint_ursus_cathedral)`. The overview is the only page with no built-in path to individual POIs.

13. **Mark done** in frontmatter:
    `python3 tools/mark_done.py location_create <path/to/main.md>`

14. **Commit** as `Create: <City Name>` — one commit per location.

## Before committing each city

Run this checklist:

- [ ] Main location file written in world66's voice (not a Wikipedia paste)
- [ ] POI count is at or near the target for the city's importance tier
- [ ] `python3 tools/wiki_geosearch.py` was run and its coordinates used
- [ ] `python3 tools/grep_obscura.py` was run; obscura matches are inspiration only
- [ ] Each new POI has coordinates that match its actual location
- [ ] Major `things_to_do` POIs have a `story:` field
- [ ] Hero image set with `image_source` and `image_license`, or explicitly skipped because none was confident
- [ ] Sections created only where they add real content
- [ ] Overview text contains markdown links to the major POIs
- [ ] `done: { location_create: <today> }` set on the main location file

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. **Research destinations — do not invent details.** Where uncertain, omit.
