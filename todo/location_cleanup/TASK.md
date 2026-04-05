# Location Cleanup Task

Get every location into shape: right sections, no junk, correct metadata. 
This is structural work — making each location match LOCATIONS.md. 
Adding new content (itineraries, books, stories) is a separate task.

Locations include cities, towns, regions, islands, and neighbourhoods. 

## For each location

0. **Is this actually worth keeping?** Many items are misclassified, misfiled, or just not useful. Make a judgement call:
   - **If it's not a location at all** (a restaurant, bar, hotel, shop, or other POI tagged `type: location`): change the type to `poi`, verify coordinates, and move it into the right section dir if needed. Delete it if the content is trivial or it's an excluded type (hotels, accommodation).
   - **If it's a location but misfiled** (wrong country, wrong parent region): usually delete — the content is almost always a stub, and don't try to reparent it.
   - **If it's a real location, keep it if either** (a) it's of genuine traveller interest (a city, a national park, a named beach, a historic town), or (b) it already has useful content worth preserving. Rewrite the overview properly.
   - **Otherwise delete it.** Tiny village stubs with one line of content ("X is a village in Y"), gibberish, SEO spam, empty "information coming soon" pages — all go. Better to have no page than a useless one.
   - **Check coordinates are plausible** for the claimed location. Wrong-country coordinates are common in old World66 data (a town in Utah with coordinates in Texas, a Milwaukee neighbourhood with coordinates in Washington State). Fix them or delete the page if the whole thing is unsalvageable.

1. **Read** the existing location file and all section/POI files

2. **Restructure sections** per LOCATIONS.md:
   - If `sights/` and/or `museums/` exist, create `things_to_do/` and move POIs in. Add `category: "Sight"` or `category: "Museum"` to each.
   - If `nightlife/` exists, move any worthwhile POIs into `bars_and_cafes/`. Delete the rest — old nightlife data is almost always outdated.
   - Delete the old section files and directories after migrating.

3. **Delete junk sections** that don't belong on location pages per LOCATIONS.md:
   - `sights.md`, `museums.md` (replaced by `things_to_do`)
   - `nightlife.md` (replaced by `bars_and_cafes`)
   - `top_5_must_dos.md`, `budget_travel_idea.md`, `family_travel_idea.md`
   - `practical_informat.md`, `7_day_itinerary.md`, `history_1.md`
   - `festivals.md` (content belongs in `when_to_go`)
   - `cybercafs.md`, `webcams.md`
   - Any duplicates (`nightlife_and_ente.md`, `museums_1.md`, `day_trips_1.md`, etc.)
   - Empty placeholder sections ("We currently have no...")
   - Spam files (gibberish filenames, wrong-country content)

4. **Fix section titles** — remove location name suffixes:
   - "Bars and Cafes in London" → "Bars and Cafes"
   - "Getting There in Paris" → "Getting There"

5. **Write section descriptions** — every section file should have a brief intro paragraph in the body
     (after the frontmatter). A section with just a title and no description looks empty. 
     2–4 sentences that orient the reader: what kind of food the place is known for, what the nightlife scene is like, how easy it is to get around. See the reference implementations in LOCATIONS.md.

6. **Review existing POIs**:
   - this is mostly true for locations, less so for regions
   - Delete spam, junk, or obviously wrong entries (sports venues, gibberish, wrong-country content)
   - Add `category` field to all POIs in `things_to_do/`
   - Check every POI has `latitude` and `longitude` — add if missing, fix if wrong
   - Verify coordinates are plausible for the location (wrong-country coords are common in old World66 data)
   - Update clearly outdated content (prices in lire, defunct businesses) where obvious

7. **Main section***
   - The main section, the markdown with the name of the location, make sure that it is a good intro for
     the location. Use the STYLE.md suggestions on how to write. Make it clear why people need to visit
     this place.
   - Add `latitude` and `longitude` to the location file if missing
   - Don't force sections on a small town — an overview alone is fine
