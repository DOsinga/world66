# LP Coverage Task

Fill gaps in World66 coverage identified by comparing against Lonely Planet's featured
destinations. These are destinations that LP prominently features — on their main
navigation, best-of lists, and top destination pages — but that World66 either lacks
entirely or has very thin coverage of (fewer than 15 POIs for a major destination).

Each batch file contains 5 content paths. Some paths already exist with a handful of POIs;
others need to be created from scratch. The path in the batch file is the canonical World66
location for that destination.

## For each location

1. **Check what's actually there — don't assume it's thin.** A destination being in this
   batch means it was identified as a potential gap, not a confirmed one. Many will turn
   out to be well-covered already, with sub-locations, POIs, and sections that the gap
   analysis missed.

   - Run `find content/<path> -name "*.md" | wc -l` to get a rough file count
   - Check for sub-locations: `ls content/<path>/` — there may already be child cities or
     regions with their own content
   - Scan the POI and section files that exist
   - If the destination is already well-covered, mark it done and move on:
     `python3 tools/mark_done.py lp_coverage <path/to/page.md>`
   - Only proceed with enrichment if there are real gaps worth filling.

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

4. **Decide the structure for this destination.**

   The approach depends on what kind of place it is:

   **Single-location destinations** (a city, a single natural site, a small island):
   Add POIs directly to the location's directory. Target:
   - Major LP-featured city (e.g. Dubrovnik, Cusco): **at least 30 POIs**
   - Natural site or park (e.g. Serengeti, Komodo, Borobudur): **10–15 POIs**
   - Small or niche destination: **the real highlights only**, however many that is

   **Regions and multi-town islands** (e.g. Cinque Terre, Corfu, Crete, Lofoten, the Algarve):
   These need one of two structures — choose based on how the destination works in practice:

   - **Use sub-locations** when the region has several distinct towns or areas worth
     covering separately. Create child location pages (e.g. `corfu/corfu_town`,
     `corfu/paleokastritsa`) each with their own POIs. The region overview page links
     to them and gives the big picture. Check if neighbouring regions in the same country
     already use this pattern. For example, Cinque Terre already has sub-location pages
     for Monterosso and Riomaggiore — Vernazza, Corniglia, and Manarola still need theirs.

   - **Use direct POIs** when the destination is best understood as a single experience —
     a national park, a single bay, a short hiking area. Add POIs directly to the region
     page: the trails, the viewpoints, the villages if they're just stops rather than
     destinations in themselves.

   If unsure, look at how LOCATIONS.md defines `region` vs `city` vs `feature`, and at
   how the destination is actually visited by travellers.

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

10. **Add hero images to the location and all sub-locations.** Every location and
    sub-location page must have an `image:` field. Use the `find-photo` skill for each
    one that is missing it. Do not auto-pick without review. Do not leave any page —
    including child city or region pages — without an image.

11. **Mark done** in frontmatter:
    `python3 tools/mark_done.py lp_coverage <path/to/page.md>`

12. **Commit** as `LP coverage: Destination Name` — one commit per location.

## Before committing each destination

- [ ] For regions/islands: either sub-locations created OR direct POIs added (not an empty region page)
- [ ] POI count is at or near the target for the destination's tier
- [ ] `python3 tools/wiki_geosearch.py` was run and useful results used
- [ ] `python3 tools/grep_obscura.py` was run; matching entries used as inspiration only
- [ ] Each new POI has coordinates matching its actual location
- [ ] Major `things_to_do` POIs have a `story:` field
- [ ] Hero image assigned via `find-photo` on the main location page, with `image_source` and `image_license`
- [ ] All sub-location pages also have hero images
- [ ] Missing useful sections created; empty-stub sections not added
- [ ] Overview text links to the major POIs
- [ ] `done: { lp_coverage: <today> }` set on the main location file

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. Research destinations —
do not invent details. Where uncertain, omit.
