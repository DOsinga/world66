# Major City Neighbourhoods Task

## Goal

Every major world city should have a set of **neighbourhood POIs** — each with a hero image and enough tagged POIs to be a genuinely useful browsing surface for a traveler.

**Quality beats quantity. Always.** A city with 7 real, characterful neighbourhoods is better than 11 where four are landmarks or parks dressed up as districts. A neighbourhood with 8 genuinely good, specific POIs is better than one padded to 15 with filler. Never invent a POI to hit a count.

## The traveler-perspective test

Before creating any neighbourhood, ask: **would a traveler consciously seek this place out and spend time here for its distinctive character?** Not "is this a useful geographic label", but "does this area have a personality — a distinct feel, a local identity, a reason to go?"

A traveler navigates to Le Marais because it has a Jewish heritage, galleries, and gay bars. They go to Kreuzberg for the counterculture and Turkish food. They go to De Pijp for the Saturday market and brown cafés. Each of these has a *reason to exist as a destination in its own right*.

**Do not create a neighbourhood just because you have a cluster of POIs in an area.** Geographic proximity is not enough. A park with several POIs inside it is a park, not a neighbourhood. A university campus with several buildings worth visiting is a campus, not a neighbourhood. A shopping street with shops is a shopping street, not a neighbourhood.

**It is fine — often correct — for many POIs to have no neighbourhood tag.** City-centre landmarks (Grafton Street, Trinity College, the Eiffel Tower area) are visited by everyone but don't belong to any one neighbourhood. Leave them untagged rather than force-assigning them.

## What is NOT a neighbourhood

Do not create a `type: neighbourhood` page for any of these:

- **A single landmark and its surroundings.** "Trinity College Area", "Dublin Castle Area", "Phoenix Park Area" are landmarks, not districts. The landmark is a POI; the surrounding area is just the city centre.
- **A park or natural area.** Phoenix Park has many POIs but it's a park. Tag those POIs `things_to_do` without a neighbourhood slug.
- **A university campus.** Trinity College, MIT, the Sorbonne — buildings on a campus are POIs; the campus itself is one POI.
- **A walking path or route.** "Philosopher's Path" is a sight you walk, not a district. Make it a `type: poi`.
- **A single market or building.** "Dilli Haat" is a craft market — a POI, not a neighbourhood.
- **An arts/craft enclave that is really part of a larger district** — tag those POIs under the parent neighbourhood instead.
- **A separate town or suburb.** If it's its own town outside the city (Portmarnock near Dublin, a coastal village), it is a `type: location` under the country/region — **not** a neighbourhood of the city.
- **The city centre itself.** "South City Centre", "Central District", "Downtown" are geographic labels, not neighbourhoods. Sub-districts within the city centre (Creative Quarter, Temple Bar, Medieval Quarter) can be neighbourhoods if they have genuine character.

A named central district with a strong, distinct identity that travelers consciously seek out **is** a valid neighbourhood, even though it sits in the middle of the city and its landmarks are visited by everyone — for example Westminster (the government and royal ceremonial quarter, holding Parliament, Westminster Abbey, and Buckingham Palace). The test is character and name recognition, not distance from the centre. When such a district exists, group its monumental landmarks under it rather than leaving them untagged; the "leave central landmarks untagged" guidance applies only to landmarks that genuinely belong to no single named district.

If you find yourself adding a `_nb`, `_area`, or `_quarter` suffix just to dodge a slug collision with a POI, that is a sign the thing is probably a POI, not a neighbourhood.

## For each city in the batch

### 1. Audit the current state

```bash
# Count existing neighbourhood POIs
find content/<path> -name "*.md" | xargs grep -l "type: neighbourhood"

# Count POIs tagged with a specific neighbourhood slug
grep -rl "<neighbourhood_slug>" content/<path>/ --include="*.md" | wc -l
```

Note which neighbourhoods already exist and how many POIs each collects. You'll be filling gaps with real content, not padding to a target.

### 2. Research first — then decide on neighbourhoods

**Start from real research, not from a quota.** Do not decide "I need 10 neighbourhoods" and then create neighbourhood pages. Instead:

1. **Look at what real named places already exist** in the city's content directory. Read the POI titles. Where do they cluster?
2. **Research the city's visitor-relevant areas** — Wikivoyage, Lonely Planet, local tourism boards. Ask: where do travelers actually *go* in this city? What areas have a distinct identity that a visitor would consciously seek out?
3. **Only create a neighbourhood page once you can name 3+ real specific places in it.** If you cannot name at least three specific, named, visitable places in an area (restaurants, museums, bars, markets, historic sites with actual addresses), that area is not ready to be a neighbourhood. Do not create the page hoping to fill it later.

The failure mode to avoid: creating a neighbourhood page for "Agdal" because Marrakesh has royal gardens in that direction, then inventing "Agdal Royal Pavilions", "Agdal Khettara Irrigation System", "Agdal Orchards" as fake sub-feature POIs to fill it. The Agdal Gardens is ONE specific place. Its sub-features are not separate POIs.

A neighbourhood needs:
- A distinct character or identity worth describing — something a traveler would specifically seek out
- A recognisable name (preferably the one locals use)
- a number of pois that match the character of the neighbourhood. Tag existing pois but if there are not enough do research to find real places that are a good fit.   


Aim for geographic spread across the city. 7–12 neighbourhoods is typical for a major city; many cities genuinely have fewer distinct traveler-relevant districts, and that is fine. **Do not reach for 10 if 6 are real and 4 would be manufactured.**

### 2b. Placement, duplicates, and overlaps — get the structure right

Before and after tagging, sanity-check the whole city:

- **One place = one entry.** Never create a POI that duplicates a neighbourhood, and never two POIs for the same place under different names. Merge them; keep the better name.
- **No overlapping neighbourhoods.** If two neighbourhoods cover the same ground, merge them and tag each POI to exactly **one** neighbourhood.
- **Is it actually IN the city, and in the right section?** A sight 30+ km away is a **day trip** (tag `day_trips`). A beach goes in `beaches`. A POI in another town belongs to that town's page.
- **Drop closed/defunct places.** Verify the place still operates before adding it.
- **Only what makes sense to a visitor.** A transit interchange, a members-only club, or a supermarket are not visitor POIs.

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
- **Coordinates** should be the approximate centre of the neighbourhood, not a single building.
- **Neighbourhood POIs carry only `things_to_do` and `neighbourhood` as tags.** Do not add `restaurant`, `bar`, or other category tags to the neighbourhood POI itself.
- Slug should be the neighbourhood's common name, lowercase with underscores: `de_pijp`, `kreuzberg`, `le_marais`.

### 4. Tag existing POIs with the neighbourhood slug

For every POI that genuinely sits within a neighbourhood, add the neighbourhood's slug to its `tags` list.

> ⚠️ **ONLY modify `tags:` — nothing else.** Do NOT add a `neighbourhood:` key, a `neighbourhood_name:` key, or any other display field. The slug in `tags:` is the only thing needed.

```yaml
# CORRECT — slug added to tags only
tags:
- things_to_do
- museum
- shilin

# WRONG — do not add this
neighbourhood: Shilin   # ← never do this
```


#### Verify geographic accuracy

Every neighbourhood tag assignment must be geographically correct. A POI that is physically outside a neighbourhood should never carry that neighbourhood's slug — even if the slug appears in the filename, the title, or the description.

**How to verify:**
1. Check the POI's `latitude` and `longitude` fields against the neighbourhood's known boundaries (use your knowledge of the city and cross-reference with OpenStreetMap or Wikivoyage boundary maps).
2. If coordinates are missing, use your knowledge of the specific named place to determine which neighbourhood it sits in — and add coordinates while you're at it.
3. Ask: "Would a person standing at these coordinates consider themselves to be in this neighbourhood?" If no, remove the tag.

**Common failure patterns to guard against:**
- A temple 4 km south of a neighbourhood tagged to it because the filename starts with the neighbourhood slug
- A building in one district tagged to an adjacent district because they "feel related"
- A day-trip destination (30+ km away) tagged to a neighbourhood
- A POI on the wrong side of a river, park, or major road that defines a neighbourhood boundary

**Before committing, do a final check:** for each neighbourhood, look at the list of POIs that carry its slug and ask whether they are plausibly within its boundaries. If any look wrong, verify the coordinates.

### 5. Create new POIs only where there are real places to add

- Ro research to find places that match the description. If the intro mention hipster cafes: we need some. If the intro mentions shopping add specific places. Only add good quality content.
- make sure coordinates are correct, use open street map

```bash
python3 tools/wiki_geosearch.py <lat> <lng> --radius 2000 --limit 30 --json
python3 tools/grep_obscura.py <country> <city>
```

Focus on the neighbourhood's character. A museum district should have museums; a dining neighbourhood needs restaurants.

Every new POI (`type: poi`) must include:
- A `score` field (float, 1.0–10.0). Calibrate against existing scored POIs in the same city. `type: neighbourhood` files do **not** get a score.
- A `snippet` field — one factual line (10–20 words) saying what the place IS. No period. No leading "A" or "The". Be specific.

#### A POI is ONE specific, named, visitable place. Do not create:

- **Category / "scene" aggregates.** "Sidi Ghanem Cafes", "Vedado Bar Scene", "Gueliz Shopping". Name the *specific* café or bar instead — or add nothing.
- **Hotels and accommodation.** Banned everywhere in this guide.
- **Activities and experiences.** "Camel rides", "Walking tour of Z". Write the *place*, not the activity.
- **Transit infrastructure.** Stations, bus interchanges, ordinary road bridges.
- **Walking routes.** A *named street that is itself a sight* (Grafton Street, Al-Muizz Street) is a fine POI; a route you trace between places is not.

**Litmus test:** can you point to one specific place on a map and name it? If not, don't create the POI.

### 6. Check section balance

```bash
grep -rl "eating_out" content/<city_path> --include="*.md" | xargs grep -l "type: poi" | wc -l
grep -rl "bars_and_cafes" content/<city_path> --include="*.md" | xargs grep -l "type: poi" | wc -l
grep -rl "things_to_do" content/<city_path> --include="*.md" | xargs grep -l "type: poi" | wc -l
```

If a section is genuinely thin and the city has real, well-known places not yet documented, adding them is worthwhile. But the same rule applies: add *named* restaurants and bars, never "Eating out in X" or "Bar scene in Y".

Also check for legacy section subdirectories (`eating_out/`, `things_to_do/`, etc. that are *directories* rather than `.md` files). If any exist, move their POIs flat to the city directory and add the right tags before continuing.

### 7. Update the city overview

If the overview mentions neighbourhoods by name, add markdown links to the neighbourhood POI pages. This is the only direct path from the overview text to a neighbourhood POI.

### 8. Commit

One commit per city: `Neighbourhoods: City Name — N neighbourhoods, M POIs tagged`

## Checklist before committing each city

- [ ] Every neighbourhood passes the traveler-perspective test — a real district with distinct character, not a geographic cluster
- [ ] No neighbourhood created for a park, campus, landmark area, or the city centre itself
- [ ] Each neighbourhood POI has an image (sourced via `find-photo`), accurate centre coordinates, and only `things_to_do` + `neighbourhood` in tags
- [ ] Each neighbourhood collects POIs that genuinely sit in it — **no POIs invented to hit a count**
- [ ] Every neighbourhood tag is geographically accurate — verify each tagged POI's coordinates fall within the neighbourhood's boundaries; remove any tags that are wrong even if the slug appears in the filename
- [ ] No `neighbourhood:` key anywhere — only the slug in `tags:` (run `grep -r "^neighbourhood:" content/<city_path>/` to verify zero results)
- [ ] No category/"scene" aggregate POIs, no hotels, no transit-station pages, no activity pages, no walking-route pages
- [ ] Every POI is one specific, named, visitable place
- [ ] Every neighbourhood is a district *inside* the city — separate towns/suburbs are `type: location`, not neighbourhoods
- [ ] No duplicate entries and no overlapping neighbourhoods
- [ ] No POI sits far outside the city in a main section — out-of-town sights are `day_trips`
- [ ] No closed/defunct places
- [ ] Every new POI has a `score` (1.0–10.0, calibrated) and a `snippet` (one specific factual line, 10–20 words, no period)
- [ ] City overview links to neighbourhood POI pages where neighbourhoods are named
- [ ] No legacy section subdirectories remain

## Reference implementations

| City | Notes |
|------|-------|
| `europe/netherlands/amsterdam` | Gold standard — 20 neighbourhoods, all with images |
| `asia/japan/tokyo` | 12 neighbourhoods, well-tagged POIs |
| `southamerica/chile/santiago` | 10 neighbourhoods, complete tagging |
| `europe/italy/lazio/rome` | Full implementation — processed in batch_0005 |
