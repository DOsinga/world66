# Location Enrich Task

## For each location

1. **Read** the existing location file and all section/POI files to understand what's already there.

2. **Spam / structure check.** Scan the location for spam, bad structure, and tag inconsistencies. Fix anything that's clearly wrong (mistyped section names, junk content, weird tags).

3. **Decide the POI target** for this city:
   - Important city (capital, major destination): **at least 50 POIs**
   - Medium importance (well-known city, common stop): **around 15 POIs**
   - Smaller place: **the real highlights**, however many that is

4. **Gather POI candidates** from all three sources — don't skip any of them:
   - `python3 tools/wiki_geosearch.py <lat> <lng> --radius 5000 --limit 25 --json` — Wikipedia geo-tagged articles near the city. **Use `--json`** so you get the `lat`/`lon` per result, not just distance. Use those coordinates when writing POIs.
   - `python3 tools/grep_obscura.py <country> <city>` — Atlas Obscura entries (off the beaten track). **Use these for inspiration only** — they identify worthwhile places to cover, but do not copy or paraphrase Atlas Obscura prose. Write the POI text from your own knowledge or independent research. Atlas Obscura content is copyrighted.
   - Your own knowledge or a web search to fill remaining gaps to the target

5. **Write POI files** at `content/<path>/<slug>.md` (flat — POIs live as siblings to the section files, not in section subdirectories, per LOCATIONS.md):
   - Each POI: at least two paragraphs of body text; longer for major sights
   - `tags:` includes the section tag (`things_to_do`, `eating_out`, etc.) and any category tags (`sight`, `museum`, `restaurant`, …)
   - `latitude` and `longitude` set — **take them from the `wiki_geosearch --json` output** when the place appears there. Do not invent coordinates from memory: a wrong coordinate puts the POI in the wrong place on the map. If the place is not in the Wikipedia results, look it up on OpenStreetMap or skip the POI.
   - For major sights with the `things_to_do` tag, add a `story:` field — 2–4 sentences, specific, surprising, accurate

6. **Add neighbourhood POIs** for large cities:
   - 3–5 characterful districts as POIs with `type: neighbourhood` and `tags: [things_to_do, neighbourhood]`
   - Tag the POIs that sit in that district with the neighbourhood slug (e.g. `tags: [eating_out, de_pijp]`)

7. **Create missing sections** where they add real value:
   - `when_to_go.md`, `getting_there.md`, `getting_around.md` if absent and the city is worth covering
   - `shopping.md`, `beaches.md`, `day_trips.md`, `books.md` where relevant
   - Skip any section that would just be a stub — LOCATIONS.md says delete-empty-section beats placeholder text

8. **Fill gaps in existing sections.** If a well-known attraction is missing, add it. If `eating_out/` or `bars_and_cafes/` is thin, add notable places.

8a. **Link POIs from the overview.** After creating POI pages, re-read the overview text and add markdown links wherever a POI name is mentioned. Example: `[Christ Church](/australiaandpacific/newzealand/northland_1/russell/christ_church)`. The overview is otherwise the only page with no path to individual POIs.

9. **Add a hero image.** If the location file has no `image:` field, invoke the `find-photo` skill — it presents candidates, you pick one, and the skill writes the `image`, `image_source`, and `image_license` fields. Do not auto-pick without review.

10. **Mark done** in frontmatter:
    `python3 tools/mark_done.py location_enrich <path/to/page.md>`

11. **Commit** as `Enrich: City Name` — one commit per location.

## Before committing each city

Run this checklist:

- [ ] POI count is at or near the target for the city's importance tier
- [ ] `python3 tools/wiki_geosearch.py` was run and the useful results used
- [ ] `python3 tools/grep_obscura.py` was run and any matching obscura POIs added
- [ ] Each new POI has coordinates that match its actual location
- [ ] Major `things_to_do` POIs have a `story:` field
- [ ] Truncated or wrong filenames in the city's directory are fixed
- [ ] Hero image assigned via `find-photo`, with `image_source` and `image_license`
- [ ] Missing useful sections created; empty-stub sections not added
- [ ] `done: { location_enrich: <today> }` set on the main location file

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. Research destinations — don't invent details.
