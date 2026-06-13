# Location Cleanup Task

Get every location into shape: right sections, no junk, correct metadata. 
This is structural work — making each location match LOCATIONS.md. 
Adding new content (itineraries, books, stories) is a separate task.

Locations include cities, towns, regions, islands, and neighbourhoods. 

## For each location

0. **Check loc_type and hierarchy placement** before anything else:
   - Every location must have `loc_type` set. Valid values: `continent`, `country`, `region`, `city`, `feature`. Set it if missing.
   - **If the parent country uses regions** (has a region level below it), this location must be inside a region — not sitting directly at the country level. If it is at the country level incorrectly, note it for the France/country-specific cleanup PR rather than moving it here.
   - **Cities** are leaf settlements (no child locations). **Features** are named areas (national parks, gorges, coastlines, named tourist areas like Cinque Terre or Normandy) — they have POIs and cities can tag into them via `tags: [feature_slug]`. **Regions** are the one grouping level below a country and contain cities and features.
   - If a location is tagged `loc_type: region` but is actually a named tourist area (Loire Valley, Côte d'Azur, Ardeche), it should be `loc_type: feature`.
   - If a location is tagged `loc_type: region` but is the country's state/province level (California, Tuscany, North France), keep it as `region`.

2. **Is this actually worth keeping?** Many items are misclassified, misfiled, or just not useful. Make a judgement call:
   - **If it's not a location at all** (a restaurant, bar, hotel, shop, or other POI tagged `type: location`): change the type to `poi`, verify coordinates, move it to sit as a sibling of the parent location's section files, and give it the right section tag (`things_to_do`, `eating_out`, `bars_and_cafes`, etc.). Delete it if the content is trivial or it's an excluded type (hotels, accommodation).
   - **If it's a location but misfiled** (wrong country, wrong parent region): usually delete — the content is almost always a stub, and don't try to reparent it.
   - **If it's a real location, keep it if either** (a) it's of genuine traveller interest (a city, a national park, a named beach, a historic town), or (b) it already has useful content worth preserving. Rewrite the overview properly.
   - **Otherwise delete it.** Tiny village stubs with one line of content ("X is a village in Y"), gibberish, SEO spam, empty "information coming soon" pages — all go. Better to have no page than a useless one.
   - **Check coordinates are plausible** for the claimed location. Wrong-country coordinates are common in old World66 data (a town in Utah with coordinates in Texas, a Milwaukee neighbourhood with coordinates in Washington State). Fix them or delete the page if the whole thing is unsalvageable.

3. **Read** the existing location file and all section/POI files. IMPORTANT: unless this is a city with 
   neighborhoods, leave the sublocations alone (for regions, states etc) - they will be processed on their
   own.

4. **Restructure sections** per LOCATIONS.md. POIs are flat — they live as siblings to the section `.md` files, not inside section subdirectories. Section membership is set by tags:
   - If `sights/` and/or `museums/` exist as directories, move the POI files up to sit alongside the section files and add `tags: [things_to_do, sight]` or `tags: [things_to_do, museum]` to each. Ensure a `things_to_do.md` section file exists.
   - If `nightlife/` exists, move any worthwhile POIs up alongside the section files and tag them `[bars_and_cafes, bar]` (or another appropriate category tag). Delete the rest — old nightlife data is almost always outdated.
   - If `things_to_do/`, `eating_out/`, `bars_and_cafes/`, `shopping/`, `beaches/`, or `books/` exist as directories, flatten them the same way: move POIs up to be siblings of the section file and rely on tags for section membership. Books are an exception — they should be inline recommendations in `books.md`, not POIs at all (see LOCATIONS.md). Delete any leftover empty directories after migrating.

5. **Delete junk sections** that don't belong on location pages per LOCATIONS.md:
   - `sights.md`, `museums.md` (replaced by `things_to_do`)
   - `nightlife.md` (replaced by `bars_and_cafes`)
   - `top_5_must_dos.md`, `budget_travel_idea.md`, `family_travel_idea.md`
   - `practical_informat.md`, `7_day_itinerary.md`, `history_1.md`
   - `festivals.md` (content belongs in `when_to_go`)
   - `cybercafs.md`, `webcams.md`
   - Any duplicates (`nightlife_and_ente.md`, `museums_1.md`, `day_trips_1.md`, etc.)
   - Empty placeholder sections ("We currently have no...")
   - Spam files (gibberish filenames, wrong-country content)

6. **Fix section titles** — remove location name suffixes:
   - "Bars and Cafes in London" → "Bars and Cafes"
   - "Getting There in Paris" → "Getting There"

7. **Write section descriptions** — every section file should have a brief intro paragraph in the body
     (after the frontmatter). A section with just a title and no description looks empty. 
     2–4 sentences that orient the reader: what kind of food the place is known for, what the nightlife scene is like, how easy it is to get around. See the reference implementations in LOCATIONS.md.

8. **Review existing POIs**:
   - this is mostly true for locations, less so for regions
   - Delete spam, junk, or obviously wrong entries (sports venues, gibberish, wrong-country content)
   - Add appropriate tags to all things-to-do POIs (e.g. `sight`, `museum`, `architecture`, `neighbourhood`) alongside their `things_to_do` section tag
   - Check every POI has `latitude` and `longitude` — add if missing, fix if wrong
   - Verify coordinates are plausible for the location (wrong-country coords are common in old World66 data)
   - Update clearly outdated content (prices in lire, defunct businesses) where obvious

9. **Main section***
   - The main section, the markdown with the name of the location, make sure that it is a good intro for
     the location. Use the STYLE.md suggestions on how to write. Make it clear why people need to visit
     this place.
   - Add `latitude` and `longitude` to the location file if missing
   - Don't force sections on a small town — an overview alone is fine

10. **Add hero image** — if the location file has no `image` field, use the `find-photo` skill to find and assign one.
