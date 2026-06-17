# Major City Neighbourhoods Task

## Goal

Every major world city should aim for **around 10 neighbourhood POIs**, each with a hero image, and a handful of **other POIs tagged** with each neighbourhood's slug so the page becomes a useful browsing surface.

**Quality beats quantity. Always.** These numbers are aspirations, not quotas. It is far better to have **fewer neighbourhoods and fewer POIs than to pad with bad content.** A neighbourhood with 6 genuinely good, specific POIs is better than one inflated to 12 with filler. A city with 7 real, characterful neighbourhoods is better than 11 where four are landmarks or markets dressed up as districts.

**Never invent a POI to hit a count.** If a neighbourhood only yields 5 real, named, visitable places, tag those 5 and move on. Do not manufacture "Bar scene in X", "Restaurants of Y", "X Metro Station", or a hotel page to reach a number. Padding is worse than thin coverage — it gets removed in review and makes the whole guide less trustworthy.

## For each city in the batch

### 1. Audit the current state

```bash
# Count existing neighbourhood POIs
find content/<path> -name "*.md" | xargs grep -l "type: neighbourhood"

# Count POIs tagged with a specific neighbourhood slug
grep -rl "<neighbourhood_slug>" content/<path>/ --include="*.md"
```

Note which neighbourhoods already exist and how many POIs each collects. You'll be filling gaps with real content, not padding to a target.

### 2. Plan the neighbourhood set

Research the city's neighbourhoods. Look for the most characterful, visitor-relevant districts — the places travellers actually go to, the areas with a distinct identity. Aim for geographic spread. Good sources: Wikivoyage, Lonely Planet, local tourism boards.

A neighbourhood needs:
- A distinct character or identity worth describing
- A recognisable name (preferably the one locals use)
- Enough real, named places within it to make the page worth visiting

**What is NOT a neighbourhood** — do not create a `type: neighbourhood` page for any of these:
- **A single landmark and its surroundings.** "Trinity College Area", "Dublin Castle Area", "Phoenix Park Area" are landmarks, not districts. The landmark is a POI; make it `type: poi`.
- **A walking path or route.** "Philosopher's Path" is a sight you walk, not a district. Make it a `type: poi`.
- **A single market or building.** "Dilli Haat" is a craft market — a POI, not a neighbourhood.
- **An arts/craft enclave that is really part of a larger district** (e.g. a single lane of galleries) — tag those POIs under the parent neighbourhood instead.
- **A separate town or suburb.** If it's its own town outside the city (Portmarnock near Dublin, a coastal village), it is a `type: location` that sits beside the city under the country/region — **not** a neighbourhood of the city. A neighbourhood is a district *inside* the city.

If you find yourself adding a `_nb`, `_area`, or `_quarter` suffix just to dodge a slug collision with a POI, that is a sign the thing is probably a POI, not a neighbourhood.

### 2b. Placement, duplicates, and overlaps — get the structure right

Before and after tagging, sanity-check the whole city against these. They catch the mistakes that look fine file-by-file but are wrong in aggregate:

- **One place = one entry.** Never create a POI that duplicates a neighbourhood (a "Chinatown" POI next to a Chinatown neighbourhood), and never two POIs for the same place under different names (Velvet Strand *is* Portmarnock Beach; the Officina Profumo *is* the Spezieria). Merge them; keep the better name.
- **No overlapping neighbourhoods.** If two neighbourhoods cover the same ground (San Frediano sits inside the Oltrarno; Pratunam blurs into Siam), merge them and tag each POI to exactly **one** neighbourhood. A POI tagged to two neighbourhoods is a signal they overlap.
- **Is it actually IN the city, and in the right section?** Check coordinates against the centre. A sight 30 km away is a **day trip**, not a `things_to_do` POI (tag it `day_trips` if the city has that section). A beach goes in the `beaches` section. A POI in another town belongs to that town's `location`, not this city.
- **Drop closed/defunct places.** Verify the place still operates. Gucci Garden (closed 2024), Fry Model Railway (closed 2010), Siam Niramit (closed 2020) are not POIs. When unsure whether somewhere niche is still open, do a quick web check before adding it.
- **Only what makes sense to a visitor.** Every neighbourhood must be somewhere a traveller would actually go and browse; every POI a specific place worth their time. A transit interchange (Victory Monument), a members-only club, a supermarket, or a road are not visitor POIs. Fewer, real entries beat a padded list.

### 3. Create missing neighbourhood POIs

For each neighbourhood that doesn't exist yet, create `content/<city_path>/<slug>.md`:

```yaml
---
title: "Neighbourhood Name"
type: neighbourhood
tags:
  - things_to_do
  - neighbourhood
latitude: <centre_lat>
longitude: <centre_lng>
image: <filename>.jpg
image_source: https://commons.wikimedia.org/wiki/File:...
image_license: CC BY-SA 4.0
---

First paragraph: what defines this neighbourhood — its character, its history, what kind of place it is. Don't start with "X is a neighbourhood in Y."

Second paragraph: the streets, landmarks, and atmosphere. Walk the reader through what they'll find. Name specific streets, squares, markets, or buildings that anchor the area.

Third paragraph (optional for large/complex neighbourhoods): what to do, eat, or drink here — a preview of the POIs within it.
```

Key rules:
- **Image is mandatory.** Use `find-photo` skill to source a Wikimedia Commons image. Don't create a neighbourhood POI without one.
- **Coordinates** should be the approximate centre of the neighbourhood, not a single building. Use OpenStreetMap to find the centroid.
- **Neighbourhood POIs carry only `things_to_do` and `neighbourhood` as tags.** Do not add `restaurant`, `bar`, or other category tags to the neighbourhood POI itself.
- Slug should be the neighbourhood's common name, lowercase with underscores: `de_pijp`, `kreuzberg`, `le_marais`.

### 4. Tag existing POIs with the neighbourhood slug

For every POI that sits geographically within a neighbourhood, add the neighbourhood's slug to its `tags` list.

> ⚠️ **ONLY modify `tags:` — nothing else.** Do NOT add a `neighbourhood:` key, a `neighbourhood_name:` key, or any other display field. The slug in `tags:` is the only thing needed. Adding `neighbourhood: Shilin` or similar is wrong and will be rejected in review.

```yaml
# CORRECT — slug added to tags only
tags:
- things_to_do
- museum
- shilin

# WRONG — do not add this
neighbourhood: Shilin   # ← never do this
```

Use the `wiki_geosearch` results and your knowledge of the city to assign POIs to neighbourhoods accurately. Tag every POI that genuinely sits in a neighbourhood. If that comes to only 5 or 6, that is fine — **do not add weak POIs to make the number bigger.**

### 5. Check section balance

Look at how many POIs the city has in each section:

```bash
grep -rl "eating_out" content/<city_path> --include="*.md" | xargs grep -l "type: poi" | wc -l
grep -rl "bars_and_cafes" content/<city_path> --include="*.md" | xargs grep -l "type: poi" | wc -l
grep -rl "things_to_do" content/<city_path> --include="*.md" | xargs grep -l "type: poi" | wc -l
```

If a section is genuinely thin and the city has real, well-known places that aren't yet documented, adding them is worthwhile. But the same rule applies: add *named* restaurants and bars, never "Eating out in X" or "Bar scene in Y".

Also check for legacy section subdirectories (`eating_out/`, `things_to_do/`, etc. that are *directories* rather than `.md` files). If any exist, move their POIs flat to the city directory and add the right tags before continuing.

### 6. Create new POIs only where there are real places to add

If a neighbourhood has real, named places worth covering that aren't documented yet, add them. Use:

```bash
python3 tools/wiki_geosearch.py <lat> <lng> --radius 2000 --limit 30 --json
python3 tools/grep_obscura.py <country> <city>
```

Focus POIs on the neighbourhood's character. A museum district should have museums; a dining neighbourhood needs restaurants; a creative district needs galleries and bars. See the `location_enrich` TASK.md for POI writing standards.

Every new POI (`type: poi`) must include:
- A `score` field (float, 1.0–10.0). Calibrate against existing scored POIs in the same city. `type: neighbourhood` files do **not** get a score.
- A `snippet` field — one factual line (10–20 words) saying what the place IS. No period. No leading "A" or "The". Be specific: name the era, cuisine, style, or what makes it notable. Example: `"Baroque church with the oldest working pipe organ in the country"` not `"Popular historic church worth visiting"`.

#### A POI is ONE specific, named, visitable place. The following are NOT POIs — do not create them:

- **Category / "scene" aggregates.** "Sidi Ghanem Cafes", "Connaught Place Restaurants", "Vedado Bar Scene", "Nørrebro Street Food", "Gueliz Shopping", "Maadi Supermarkets", "Heliopolis Commercial Arcades". If the title is `<Place> <plural category>` or `<Place> Scene`, it is filler. Name the *specific* café, restaurant, or bar instead — or add nothing.
- **Hotels and accommodation.** Banned everywhere in this guide (see CLAUDE.md). No Four Seasons, Kempinski, La Mamounia, "boutique hotels", "spa retreats", guesthouses. (A genuinely iconic building that happens to contain a hotel — e.g. an Art Deco landmark or famous observation tower — is acceptable *as the landmark*, written about as a sight, not a place to stay.)
- **Activities and experiences.** "Camel rides", "Hot air balloon over X", "Cycling the Y perimeter", "X at sunrise", "Walking tour of Z", "Cooking class". These are things you do, not places. Write the *place* (the grove, the park, the street) if it merits a POI.
- **Transit infrastructure.** Metro/LRT/railway stations, bus interchanges, "X Station Area", ordinary road bridges. (A bridge or station that is itself a famous landmark — Ha'penny Bridge, a historic terminus — is fine *as a sight*.)
- **Walking routes.** "X Evening Walk", "Heritage Walk", "Canal Walk", "Neighbourhood Walk". A *named street that is itself a sight* (Grafton Street, Victoria Street, Al-Muizz Street) is a fine POI; a route you trace between places is not.

**Litmus test:** can you point to one specific place on a map and name it? If not, don't create the POI. When in doubt, leave it out — fewer, real POIs always win.

### 7. Update the city overview

If the overview mentions neighbourhoods by name, add markdown links to the neighbourhood POI pages. This is the only direct path from the overview text to a neighbourhood POI.

### 8. Commit

One commit per city: `Neighbourhoods: City Name — N neighbourhoods, M POIs tagged`

## Checklist before committing each city

- [ ] Every neighbourhood is a real district — not a single landmark, market, or walking path (those are POIs)
- [ ] Each neighbourhood POI has an image (sourced via `find-photo`), accurate centre coordinates, and only `things_to_do` + `neighbourhood` in tags
- [ ] Each neighbourhood collects the POIs that genuinely sit in it — **no POIs invented to hit a number**
- [ ] No `neighbourhood:` key anywhere — only the slug in `tags:` (run `grep -r "^neighbourhood:" content/<city_path>/` to verify zero results)
- [ ] No category/"scene" aggregate POIs (no "X Restaurants", "X Bar Scene", "X Street Food", "X Galleries")
- [ ] No hotels/accommodation, no transit-station pages, no activity/experience pages, no walking-route pages
- [ ] Every POI is one specific, named, visitable place
- [ ] Every neighbourhood is a district *inside* the city — separate towns/suburbs are `type: location`, not neighbourhoods
- [ ] No duplicate entries (a POI duplicating a neighbourhood; two POIs for the same place) and no overlapping neighbourhoods
- [ ] No POI sits far outside the city in a main section — out-of-town sights are `day_trips`, beaches are in `beaches`
- [ ] No closed/defunct places (verify anything niche still operates)
- [ ] Every new POI has a `score` (1.0–10.0, calibrated) and a `snippet` (one specific factual line, 10–20 words, no period)
- [ ] City overview links to neighbourhood POI pages where neighbourhoods are named
- [ ] No legacy section subdirectories remain (any `eating_out/`, `things_to_do/` *directories* have been flattened)

## Reference implementations

| City | Notes |
|------|-------|
| `europe/netherlands/amsterdam` | Gold standard — 20 neighbourhoods, all with images |
| `asia/japan/tokyo` | 12 neighbourhoods, well-tagged POIs |
| `southamerica/chile/santiago` | 10 neighbourhoods, complete tagging |
| `europe/italy/lazio/rome` | Full implementation — processed in batch_0005 |
