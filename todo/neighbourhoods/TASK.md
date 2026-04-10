# Neighbourhoods Task

Add a rich neighbourhood section to major cities — a guide to the city's distinct neighbourhoods and areas, each with a proper intro, a hero image, and cross-references to the POIs already listed in other sections.

This task is for **major cities only**. Each batch contains exactly one city.

## Before you start — checks

Run these checks on the city before doing any writing. Fix problems first, then proceed.

### 1. Location cleanup done?

Check the city's main `.md` file for `done: location_cleanup`. If it's missing, run the location_cleanup task first or skip this city and pick another batch.

### 2. Enough POIs?

Count POIs across `things_to_do/`, `eating_out/`, and `bars_and_cafes/`. A city needs **at least 15 POIs total** to support meaningful neighbourhood tagging. If it's thin:

- Check if the POI directories exist at all — if not, the cleanup wasn't done properly, skip it.
- If there are 8–14 POIs, proceed but only tag what exists; note the gap in the commit message.
- If there are fewer than 8, skip this city.

### 3. Coordinate sanity check

For every POI that has `latitude` and `longitude`, verify the coordinates are plausible for this city. A quick rule: look up the city's approximate bounding box and flag any POI whose coordinates fall outside it. Common failures:

- Coordinates of `0, 0` — missing data pasted as null
- Coordinates in a completely different country (e.g., a Paris POI with New York coordinates)
- Coordinates that look swapped (lat/lng reversed)

Fix bad coordinates before tagging POIs to neighbourhoods — a POI with wrong coordinates on a neighbourhood map is worse than no POI.

To fix: look up the correct coordinates for the place (use web search), update the file, note the fix in the commit message.

### 4. Neighbourhood POIs in things_to_do?

Check for POIs with `category: "Neighbourhood"` in `things_to_do/`. These are neighbourhoods masquerading as POIs and must be **converted** to proper neighbourhood files at the city root:

1. Read the existing POI body — use it as the starting point for the neighbourhood file.
2. Create `<slug>.md` at the city root with `type: neighbourhood` and expanded content (3–5 paragraphs).
3. Delete the original `things_to_do/<slug>.md` POI file.
4. Add a redirect in `redirects.json`: `"city/things_to_do/slug"` → `"city/slug"`.

Do not leave a `category: "Neighbourhood"` POI in `things_to_do/` once its neighbourhood page exists.

### 5. Section structure correct?

Confirm the city uses `things_to_do/` (not `sights/` or `museums/`), and that `bars_and_cafes/` exists if relevant. If old section names are still present, do a quick structural fix first (or note it and skip tagging those POIs).

## Flatten and tag POIs

Before building neighbourhood pages, migrate the city's POIs to the tag-based model. This unlocks neighbourhood cross-referencing and keeps all POI files in one place.

For each section subdirectory (`things_to_do/`, `eating_out/`, `bars_and_cafes/`, `shopping/`, `day_trips/`, etc.):

1. **Add tags** to each POI file:
   - Add `tags:` containing the section slug: `tags: [things_to_do]`
   - If the POI has a `neighbourhood:` field, also add the neighbourhood slug as a tag: `tags: [things_to_do, jordaan]`
   - A POI can have multiple section tags if it genuinely fits more than one

2. **Move the file** from `section_name/poi.md` to `poi.md` at the city root. The old URL (`city/section_name/poi`) continues to work via tag routing — no redirect needed.

3. Leave the section `.md` file (`things_to_do.md`) in place — it defines the section and its description.

**Do not flatten:**
- Section files (`things_to_do.md`, `eating_out.md`, etc.)
- Child location directories (e.g. `districts/shoreditch.md`) — handle those under "Cities with sub-locations"
- Files already at city root

After this step the city root will contain many more files. That is correct — all POIs are now peers of the section files, discoverable by tag.

## What to build

For each city, create:

1. **`neighbourhoods.md`** — the section group file
2. **`<neighbourhood_slug>.md`** — one file per neighbourhood at the city root (15–25 for a world capital, 8–15 for a smaller major city)
3. **`<neighbourhood_slug>/<local_poi_slug>.md`** — neighbourhood-local streets, squares, and parks

### Section group file (`neighbourhoods.md`)

```yaml
---
title: "Neighbourhoods"
type: section_group
---

Brief intro (2–3 sentences) describing how the city divides into areas and why it's worth exploring neighbourhood by neighbourhood.
```

The `type: section_group` makes this a container that groups all `neighbourhood` pages in the city sidebar.

### Neighbourhood file (`jordaan.md` — at city root)

```yaml
---
title: "Jordaan"
type: neighbourhood
latitude: 52.3738
longitude: 4.8827
image: jordaan.jpg
image_source: "https://commons.wikimedia.org/wiki/File:..."
image_license: "CC BY-SA 4.0"
---

[3–5 paragraphs about the neighbourhood: its character, history, what it looks like, what draws people there, what time of day is best, what makes it different from adjacent areas.]
```

The `type: neighbourhood` is a NAV_TYPE — it appears in the city sidebar and collects POIs by tag. Any POI with `tags: [jordaan]` (matching the slug) will appear on this neighbourhood page automatically.

### Neighbourhood writing guide

- **Specific and vivid.** Name streets, squares, markets, buildings. Not "there are many cafes" but "the cafes along Exmouth Market spill onto the pavement".
- **Character over logistics.** What does it feel like? What kind of people live there? What's the history?
- **Honest about rougher edges.** If part of an area is under construction or touristed to death, say so.
- **3–5 paragraphs minimum** for major neighbourhoods. Smaller satellite areas can be shorter.
- **Research using web search** — do not invent details, street names, or history.
- **Link to local POIs by name.** When the body text mentions a street, square, park, or market that has a POI file, link the name directly. Use the full URL path: `[Bloemgracht](/europe/netherlands/amsterdam/jordaan/bloemgracht)`. If the same name appears multiple times, link only the first occurrence. This applies to both neighbourhood-local POIs (in `<slug>/`) and city-root POIs tagged to the neighbourhood.

### Images

Every neighbourhood file must have `image`, `image_source`, and `image_license` in its frontmatter, and the image file must be physically present at `<slug>.jpg` (or `.png`) alongside the `.md` file at the city root.

**How to fetch images from Wikipedia/Wikimedia Commons:**

For each neighbourhood, query the Wikipedia API for the page thumbnail:

```
https://en.wikipedia.org/w/api.php?action=query&titles=TITLE&prop=pageimages&piprop=thumbnail&pithumbsize=800&format=json
```

Use the thumbnail URL to download the image. The Wikimedia API allows thumbnail sizes — request 800px to stay within rate limits. Then query Commons for the license:

```
https://commons.wikimedia.org/w/api.php?action=query&titles=File:FILENAME&prop=imageinfo&iiprop=extmetadata&format=json
```

If the Wikipedia page has no thumbnail, search Wikimedia Commons directly:

```
https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=QUERY&gsrnamespace=6&prop=imageinfo&iiprop=url|extmetadata|mime&format=json
```

Pick the first result with a JPEG or PNG mime type. Use the full image URL from `imageinfo.url`.

**Frontmatter format:**
```yaml
image: jordaan.jpg
image_source: "https://commons.wikimedia.org/wiki/File:Prinsengracht_Jordaan.jpg"
image_license: "CC BY-SA 4.0"
```

The image file lives at the city root alongside the neighbourhood `.md` file. Add 1–2 seconds of delay between requests to avoid rate limiting.

### Tagging POIs

After creating the neighbourhood files, go through the city's POIs (now at the city root after flattening) and ensure each POI that belongs to a neighbourhood has:

1. `neighbourhood: "Exact Title"` — must match the neighbourhood file's `title:` exactly (case-sensitive)
2. The neighbourhood slug in its `tags:` list — e.g. `tags: [things_to_do, jordaan]`

Both are needed: `neighbourhood:` is displayed in the info box; the slug tag is what wires the POI to the neighbourhood page via `tagged_pois()`.

### Neighbourhood-local streets, squares, and parks

For each neighbourhood, add POI files for the streets, squares, and parks that give the area its character — the market, the main shopping street, the local park, the canal worth walking. These are stored in `<neighbourhood_slug>/` subdirectories at the city root and appear **only on the neighbourhood page**, not in city-section listings.

**What belongs here vs in city sections:**

- **City-level** (keep as a city-root POI with section tag + neighbourhood slug tag): only if the street is a genuine destination on its own — a famous market street, a well-known nightlife strip, a park people travel across the city for.
- **Neighbourhood-level only** (store in `<slug>/` subdirectory): streets, squares, and parks that reward knowing about but are not city-level destinations. A beautiful canal that only locals seek out. A neighbourhood market. A local park.

**Aim for 3–6 neighbourhood-local POIs per neighbourhood.** Each must have:
- `type: poi`
- `category: "Street"`, `category: "Square"`, or `category: "Park"`
- `tags: [neighbourhood_slug]` — this is how `tagged_pois()` finds them
- `latitude` and `longitude`

Example: `amsterdam/jordaan/bloemgracht.md` with `tags: [jordaan]`.

**Aim for coverage across the full neighbourhood geography:**
- The park or green space people use daily
- The main commercial artery
- The market, if there is one (city-level if famous enough)
- A cross-street or boundary road that defines the neighbourhood's shape
- A quieter canal or side street that gives the area its character
- A secondary shopping or restaurant street

## Cities with sub-locations

Some major cities (London, Tokyo, etc.) have districts stored as separate child locations — e.g. `london/shoreditch.md` with `type: location`, with its own `things_to_do/`, `eating_out/` subdirectories. **Always convert these to neighbourhood pages.** There is no case where a sub-location should stay as a `type: location` inside a city.

1. **Convert to a neighbourhood file.** Change `type: location` to `type: neighbourhood`. The file stays at its current city-root path (e.g. `london/shoreditch.md`).
2. **Flatten the sub-location's POIs.** Apply the same POI flattening step as for the city itself: move POI files from `shoreditch/things_to_do/poi.md` to the city root (`london/poi.md`) and add `tags: [things_to_do, shoreditch]`.
3. **Delete the sub-location's section files and empty directories.** Once POIs are at the city root, remove `shoreditch/things_to_do.md`, `shoreditch/eating_out.md`, etc. Remove now-empty directories.
4. **Redirect if the URL changed.** If the sub-location moved (e.g. from `london/districts/shoreditch` to `london/shoreditch`), add a redirect in `redirects.json`.

The goal is a single flat city structure: all POIs at the city root with tags, all neighbourhoods as `type: neighbourhood` pages at the city root.

## What makes a good neighbourhood list

Cover the full city — don't only do the tourist centre. Include:

- The historic core and main tourist areas
- Up-and-coming and creative quarters
- Traditional working-class areas
- Waterfront or riverside areas where they exist
- University districts
- Ethnic enclaves and market areas
- The "locals go here" neighbourhoods

For London: aim for 20+. For cities like Krakow or Amman: 8–12 is fine.

## Commit format

```
Neighbourhoods: City Name
```

One commit per city (the whole batch is one city).

## Done stamp

Add to the city's main `.md` file:

```yaml
done:
  neighbourhoods: <today's date>
```

(alongside any existing `done:` entries)

## Commit message format

```
Neighbourhoods: City Name

- N neighbourhoods created
- M POIs tagged across things_to_do/, eating_out/, bars_and_cafes/
- X bad coordinates fixed (list them)
- any other notable issues
```
