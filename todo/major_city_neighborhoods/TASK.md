# Major City Neighbourhoods Task

## Goal

Every major world city should aim for **around 10 neighbourhood POIs**, each with a hero image, and **around 20 other POIs** (across all sections) tagged with each neighbourhood's slug. These are targets, not hard minimums — a city with 6 well-chosen neighbourhoods is fine, and a neighbourhood with 12 well-tagged POIs is better than a neighbourhood with 20 thin ones. The goal is that neighbourhood pages become genuinely useful browsing surfaces.

## For each city in the batch

### 1. Audit the current state

```bash
# Count existing neighbourhood POIs
find content/<path> -name "*.md" | xargs grep -l "type: neighbourhood"

# Count POIs tagged with a specific neighbourhood slug
grep -rl "<neighbourhood_slug>" content/<path>/ --include="*.md"
```

Note which neighbourhoods already exist and how many POIs each collects. You'll be filling gaps, not replacing what's there.

### 2. Plan the neighbourhood set

Research the city's neighbourhoods. Look for the 10–15 most characterful, visitor-relevant districts — the places travellers actually go to, the areas with a distinct identity. Aim for geographic spread across the city. Good sources: Wikivoyage, Lonely Planet, local tourism boards.

Each neighbourhood needs:
- A distinct character or identity worth describing
- Enough attractions, restaurants, and bars to collect 20+ POIs
- A recognisable name (preferably the one locals use)

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

```yaml
# Before
tags:
  - eating_out
  - restaurant

# After
tags:
  - eating_out
  - south_bank
  - restaurant
```

Use the `wiki_geosearch` results and your knowledge of the city to assign POIs to neighbourhoods accurately. If a POI is clearly in a specific area, tag it — don't leave POIs unassigned.

**Target: each neighbourhood page should collect around 20 POIs.** If an existing neighbourhood has fewer, add more where there are real things worth covering — but don't pad with weak POIs just to hit a number.

### 5. Check section balance

Before adding POIs, look at how many the city has in each section:

```bash
grep -rl "eating_out" content/<city_path> --include="*.md" | xargs grep -l "type: poi" | wc -l
grep -rl "bars_and_cafes" content/<city_path> --include="*.md" | xargs grep -l "type: poi" | wc -l
grep -rl "things_to_do" content/<city_path> --include="*.md" | xargs grep -l "type: poi" | wc -l
```

A major city should have at least 10–15 restaurants and 10+ bars/cafes. If a section is thin, adding POIs there is just as important as neighbourhood tagging. **Amsterdam, for example, has only 3 eating_out POIs — a city that size needs 15–20 good restaurants documented.**

Also check for legacy section subdirectories (`eating_out/`, `things_to_do/`, etc. that are *directories* rather than `.md` files). If any exist, move their POIs flat to the city directory and add the right tags before continuing.

### 6. Create new POIs if needed

If a neighbourhood doesn't have enough POIs to reach 20, add them. Use:

```bash
python3 tools/wiki_geosearch.py <lat> <lng> --radius 2000 --limit 20 --json
python3 tools/grep_obscura.py <country> <city>
```

Focus POIs on the neighbourhood's character. A museum district should have museums; a dining neighbourhood needs restaurants; a creative district needs galleries and bars. See the `location_enrich` TASK.md for POI writing standards.

Every new POI (`type: poi`) must include a `score` field (float, 1.0–10.0). Calibrate against existing scored POIs in the same city — if the city already has a 9.0 for its most iconic sight, score new POIs relative to that. `type: neighbourhood` files do **not** get a score.

### 6. Update the city overview

If the overview mentions neighbourhoods by name, add markdown links to the neighbourhood POI pages. This is the only direct path from the overview text to a neighbourhood POI.

### 7. Commit

One commit per city: `Neighbourhoods: City Name — N neighbourhoods, M POIs tagged`

## Checklist before committing each city

- [ ] City has as many neighbourhood POIs as makes sense (target ~10)
- [ ] Each neighbourhood POI has an image (sourced via `find-photo`)
- [ ] Each neighbourhood POI has accurate coordinates
- [ ] Each neighbourhood POI has only `things_to_do` and `neighbourhood` in tags
- [ ] Each neighbourhood collects as many POIs as possible (target ~20) via its slug tag
- [ ] City overview links to neighbourhood POI pages where neighbourhoods are named
- [ ] Every new POI has a `score` field (1.0–10.0), calibrated against existing city POIs
- [ ] `eating_out` has at least 10–15 POIs for a major city (add restaurants if thin)
- [ ] No legacy section subdirectories remain (any `eating_out/`, `things_to_do/` *directories* have been flattened)

## Reference implementations

| City | Notes |
|------|-------|
| `europe/netherlands/amsterdam` | Gold standard — 20 neighbourhoods, all with images |
| `asia/japan/tokyo` | 12 neighbourhoods, well-tagged POIs |
| `southamerica/chile/santiago` | 10 neighbourhoods, complete tagging |
| `europe/italy/lazio/rome` | Partial (3) — shows the tagging pattern in action |
