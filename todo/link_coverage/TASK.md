# Link Coverage Task

Fill gaps in World66 coverage identified by **broken internal links**. Other content pages
already reference these places — sometimes from multiple sources — but no page exists for
them yet. They were classified as "Bucket 1 — Recreate" in `BROKEN_LINKS_AUDIT.tsv`.

Each batch file contains 5 content paths. Most are missing locations (cities, regions,
features, islands); a few are missing POIs under existing cities. The path in the batch
file is the URL the broken link points to, with the leading slash stripped.

## For each path

1. **Find who links to it.** Before writing anything, locate the existing pages that
   reference this URL so you understand the context — what the linkers say about the
   place, what kind of page (location vs POI) they expect:
   ```
   grep -rl "(/<batch_path>)" content/
   ```
   Read 1–2 of those source files. Their prose often names the country, the region, or
   what makes the place worth visiting — useful raw material.

2. **Decide what kind of page this should be.** The URL depth and the linkers' wording
   are the strongest hints:
   - `/continent/country` — a country page (rare; only if the country itself was missing)
   - `/continent/country/X` — usually a city/region/feature directly under the country
   - `/continent/country/region/X` — usually a city under a region (or sometimes a POI)
   - `/continent/country/.../<X>/<Y>` — likely a POI under an existing city/feature
   If it's a POI, the parent location must already exist — verify with `find` first.

3. **Check what's already there.** Run `find content -iname '<slug>.md'` using the last
   path segment. Also try no-underscore and diacritic-folded variants (e.g. `phu_quoc`
   and `phuquoc`). If the file exists at a different path than the batch entry, the
   broken link is a Bucket-2 (rewrite) miss — fix the source links instead of creating
   a new page, then mark the batch entry done.

4. **If the file does not exist yet, create it.** Look at how neighbouring locations in
   the same country are structured. Write a 2–4 paragraph overview in world66's voice:
   practical, opinionated, concise. Do not copy from Wikipedia, Wikivoyage, or any
   other source.

   For **locations**, frontmatter must include:
   - `title:` — the destination name
   - `type: location`
   - `loc_type:` — `city`, `region`, `island`, or `feature` (national park, natural site)
   - `latitude:` and `longitude:` — from Wikipedia geo-search or OpenStreetMap

   For **POIs**, frontmatter must include:
   - `title:` — the POI name
   - `type: poi`
   - `tags:` — at minimum the section tag (`things_to_do`, `eating_out`, etc.) and one
     or more category tags (`sight`, `museum`, `restaurant`, `nature`, `beach`, …)
   - `latitude:` and `longitude:` from the wiki_geosearch JSON or OpenStreetMap

5. **Decide the POI target** for the new location:
   - Major city/region clearly worth a visit: **at least 25 POIs**
   - Scenic region, island, or smaller city: **15–25 POIs**
   - Natural site or park: **10–15 POIs**
   - Small or niche destination: **the real highlights only**, however many that is
   - Single missing POI (not a location): no extra POIs needed beyond the entry itself

6. **Gather POI candidates** from all three sources — don't skip any:
   - `python3 tools/wiki_geosearch.py <lat> <lng> --radius 5000 --limit 25 --json` —
     Wikipedia geo-tagged articles nearby. **Use `--json`** to get `lat`/`lon` per result.
     For parks/regions, increase `--radius`.
   - `python3 tools/grep_obscura.py <country> <city>` — Atlas Obscura entries for the
     destination. **Use for inspiration only** — do not copy or paraphrase Atlas Obscura
     prose. Write the POI text from your own knowledge.
   - Your own knowledge or a web search to fill remaining gaps to the target.

7. **Write POI files** at `content/<path>/<poi_slug>.md` (flat — POIs live as siblings
   to section files, not in section subdirectories):
   - Each POI: at least two paragraphs of body text; longer for major sights
   - `tags:` includes the section tag and any category tags
   - `latitude` and `longitude` set — take them from `wiki_geosearch --json` when the
     place appears. Don't invent coordinates from memory. If not in Wikipedia results,
     look it up on OpenStreetMap or skip the POI.
   - For major sights with `things_to_do`, add a `story:` field — 2–4 sentences,
     specific, surprising, accurate.

8. **Create sections** where they add real value (don't create stubs):
   - `when_to_go.md`, `getting_there.md`, `getting_around.md` for any covered destination
     — but per LOCATIONS.md, only add a `when_to_go` if it differs substantively from
     the parent country
   - `beaches.md`, `day_trips.md`, `books.md`, `shopping.md` where relevant
   - Skip any section that would just be a placeholder paragraph

9. **Add neighbourhood POIs** for large cities:
   - 3–5 characterful districts as POIs with `type: neighbourhood` and
     `tags: [things_to_do, neighbourhood]`
   - Tag the POIs that sit in that district with the neighbourhood slug

10. **Link POIs from the overview.** After creating POI pages, re-read the overview and
    add markdown links wherever a POI name is mentioned.

11. **Verify the broken-link signal is resolved.** Re-run the linter and confirm the
    target URL no longer appears in the `broken_link` report:
    ```
    python3 tools/linter.py 2>&1 | grep '<batch_path>'
    ```
    Expect no output.

12. **Add a hero image — both the file AND the frontmatter.** Use `tools/find_photo.py`:
    ```
    python3 tools/find_photo.py --no-classify /<continent>/<country>/.../<slug>
    ```
    The path is `/europe/austria/salzkammergut` (leading slash, no `content/` prefix,
    no `.md`). The script prints candidate thumbnails as JSON. Pick the best by reading
    the thumbnail files (`thumb_path` field). Then:
    ```
    python3 tools/find_photo.py --select-meta '<json-of-chosen-candidate>' /<continent>/<country>/.../<slug>
    ```
    This downloads the full image, resizes it, saves it next to the `.md`, AND writes
    the `image:` / `image_source:` / `image_license:` / `image_attribution:` frontmatter
    fields — all in one call.

    If `find_photo.py` finds no suitable candidate (exit code 1, empty `candidates`
    array), leave the hero image off entirely. Don't fabricate sources.

13. **Mark done** in frontmatter:
    `python3 tools/mark_done.py link_coverage <path/to/page.md>`

14. **Commit** as `Link coverage: Destination Name` — one commit per location.

## Before committing each destination

- [ ] POI count is at or near the target for the destination's tier
- [ ] `python3 tools/wiki_geosearch.py` was run and useful results used
- [ ] `python3 tools/grep_obscura.py` was run; matching entries used as inspiration only
- [ ] Each new POI has coordinates matching its actual location
- [ ] Major `things_to_do` POIs have a `story:` field
- [ ] Hero image assigned via `find-photo`, with `image_source` and `image_license`
- [ ] Missing useful sections created; empty-stub sections not added
- [ ] Overview text links to the major POIs
- [ ] `done: { link_coverage: <today> }` set on the main location file
- [ ] The original broken link no longer appears in `python3 tools/linter.py` output

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise. Research destinations —
do not invent details. Where uncertain, omit.
