# LP Coverage Task

Fill gaps in World66 coverage identified by comparing against Lonely Planet's featured
destinations. These are destinations that LP prominently features — on their main
navigation, best-of lists, and top destination pages — but that World66 either lacks
entirely or has very thin coverage of (fewer than 15 POIs for a major destination).

Each batch file contains 5 content paths. Some paths already exist with a handful of POIs;
others need to be created from scratch. The path in the batch file is the canonical World66
location for that destination.

## For each location

1. **Check what's already there.** Read the existing location `.md` file (if any) and all
   files in the location's directory. Note the current POI count and what sections exist.

2. **If the location file does not exist yet, create it.** Look at how neighbouring
   locations in the same country are structured (check siblings in the parent directory).
   Write a 2–4 paragraph overview in world66's voice: practical, opinionated, concise.
   Do not copy from Wikipedia, Wikivoyage, or any other source.
   Frontmatter must include:
   - `title:` — the destination name
   - `type: location`
   - `loc_type:` — `city`, `region`, `island`, or `feature` (national park, natural site)
   - `latitude:` and `longitude:` — from Wikipedia geo-search or OpenStreetMap
   - `country:` — parent country name

3. **Fix any structure issues** on existing pages: wrong tags, truncated filenames, spam,
   misplaced sections, missing `type:` fields.

4. **Decide the POI target** for this destination:
   - Major LP-featured city (e.g. Dubrovnik, Cusco): **at least 30 POIs**
   - Scenic region or island (e.g. Cinque Terre, Crete, Lofoten): **15–25 POIs**
   - Natural site or park (e.g. Serengeti, Komodo, Borobudur): **10–15 POIs**
   - Small or niche destination: **the real highlights only**, however many that is

5. **Gather POI candidates** from all three sources — don't skip any:
   - `python3 tools/wiki_geosearch.py <lat> <lng> --radius 5000 --limit 25 --json` —
     Wikipedia geo-tagged articles nearby. **Use `--json`** to get `lat`/`lon` per result.
     Use those coordinates when writing POIs. For parks/regions, increase `--radius`.
   - `python3 tools/grep_obscura.py <country> <city>` — Atlas Obscura entries for the
     destination. **Use for inspiration only** — do not copy or paraphrase Atlas Obscura
     prose. Write the POI text from your own knowledge or independent research.
   - Your own knowledge or a web search to fill remaining gaps to the target.

6. **Write POI files** at `content/<path>/<poi_slug>.md` (flat — POIs live as siblings to
   section files, not in section subdirectories):
   - Each POI: at least two paragraphs of body text; longer for major sights
   - `tags:` includes the section tag (`things_to_do`, `eating_out`, etc.) and any
     category tags (`sight`, `museum`, `restaurant`, `beach`, `nature`, …)
   - `latitude` and `longitude` set — take them from the `wiki_geosearch --json` output
     when the place appears there. Do not invent coordinates from memory. If a place is
     not in the Wikipedia results, look it up on OpenStreetMap or skip the POI.
   - For major sights with the `things_to_do` tag, add a `story:` field — 2–4 sentences,
     specific, surprising, accurate.

7. **Create sections** where they add real value (don't create stubs):
   - `when_to_go.md`, `getting_there.md`, `getting_around.md` for any covered destination
   - `beaches.md`, `day_trips.md`, `books.md`, `shopping.md` where relevant
   - Skip any section that would just be a placeholder paragraph

8. **Add neighbourhood POIs** for large cities:
   - 3–5 characterful districts as POIs with `type: neighbourhood` and
     `tags: [things_to_do, neighbourhood]`
   - Tag the POIs that sit in that district with the neighbourhood slug

9. **Link POIs from the overview.** After creating POI pages, re-read the overview and
   add markdown links wherever a POI name is mentioned.

10. **Add a hero image.** If the location file has no `image:` field, invoke the
    `find-photo` skill. Do not auto-pick without review.

11. **Mark done** in frontmatter:
    `python3 tools/mark_done.py lp_coverage <path/to/page.md>`

12. **Commit** as `LP coverage: Destination Name` — one commit per location.

## Before committing each destination

- [ ] POI count is at or near the target for the destination's tier
- [ ] `python3 tools/wiki_geosearch.py` was run and useful results used
- [ ] `python3 tools/grep_obscura.py` was run; matching entries used as inspiration only
- [ ] Each new POI has coordinates matching its actual location
- [ ] Major `things_to_do` POIs have a `story:` field
- [ ] Hero image assigned via `find-photo`, with `image_source` and `image_license`
- [ ] Missing useful sections created; empty-stub sections not added
- [ ] Overview text links to the major POIs
- [ ] `done: { lp_coverage: <today> }` set on the main location file

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. Research destinations —
do not invent details. Where uncertain, omit.
