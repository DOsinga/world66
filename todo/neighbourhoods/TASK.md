# Neighbourhoods Task

Add a rich `explore` section to major cities — a guide to the city's distinct neighbourhoods and areas, each with a proper intro, a hero image, and cross-references to the POIs already listed in other sections.

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

Check for POIs with `category: "Neighbourhood"` in `things_to_do/`. These are neighbourhoods masquerading as POIs and must be **converted** to proper neighbourhood files in `explore/`:

1. Read the existing POI body — use it as the starting point for the neighbourhood file.
2. Create `explore/<slug>.md` with `type: neighbourhood` and expanded content (3–5 paragraphs).
3. Delete the original `things_to_do/<slug>.md` POI file.
4. Add a redirect in `redirects.json`: `"city/things_to_do/slug"` → `"city/explore/slug"`.

Do not leave a `category: "Neighbourhood"` POI in `things_to_do/` once its neighbourhood page exists.

### 5. Section structure correct?

Confirm the city uses `things_to_do/` (not `sights/` or `museums/`), and that `bars_and_cafes/` exists if relevant. If old section names are still present, do a quick structural fix first (or note it and skip tagging those POIs).

## What to build

For each city, create:

1. **`explore.md`** — the section file
2. **`explore/neighbourhood_slug.md`** — one file per neighbourhood (15–25 for a world capital, 8–15 for a smaller major city)

### Section file (`explore.md`)

```yaml
---
title: "Explore by Neighbourhood"
type: section
---

Brief intro (2–3 sentences) describing how the city divides into areas and why it's worth exploring neighbourhood by neighbourhood.
```

### Neighbourhood file (`explore/soho.md`)

```yaml
---
title: "Soho"
type: neighbourhood
latitude: 51.5137
longitude: -0.1337
image: soho.jpg
image_source: "https://commons.wikimedia.org/wiki/File:..."
image_license: "CC BY-SA 4.0"
---

[3–5 paragraphs about the neighbourhood: its character, history, what it looks like, what draws people there, what time of day is best, what makes it different from adjacent areas.]
```

The `type: neighbourhood` distinguishes these from regular sections and locations.

### Neighbourhood writing guide

- **Specific and vivid.** Name streets, squares, markets, buildings. Not "there are many cafes" but "the cafes along Exmouth Market spill onto the pavement".
- **Character over logistics.** What does it feel like? What kind of people live there? What's the history?
- **Honest about rougher edges.** If part of an area is under construction or touristed to death, say so.
- **3–5 paragraphs minimum** for major neighbourhoods. Smaller satellite areas can be shorter.
- **Research using web search** — do not invent details, street names, or history.
- **Link to local POIs by name.** When the body text mentions a street, square, park, or market that has a POI file in `explore/<slug>/` or in the city's sections, link the name directly. Use the full URL path: `[Bloemgracht](/europe/netherlands/amsterdam/explore/jordaan/bloemgracht)`. If the same name appears multiple times, link only the first occurrence. This applies to both neighbourhood-local POIs (in `explore/<slug>/`) and city-section POIs (in `shopping/`, `bars_and_cafes/`, etc.) that are tagged to the neighbourhood. For example, in the De Pijp page: link [Albert Cuypmarkt](/europe/netherlands/amsterdam/shopping/albert_cuypmarkt), [Ceintuurbaan](/europe/netherlands/amsterdam/explore/de_pijp/ceintuurbaan), [Ferdinand Bolstraat](/europe/netherlands/amsterdam/explore/de_pijp/ferdinand_bolstraat), [Van Woustraat](/europe/netherlands/amsterdam/explore/de_pijp/van_woustraat), and [Sarphatipark](/europe/netherlands/amsterdam/explore/de_pijp/sarphatipark) where they appear in the text.

### Images

Every neighbourhood file must have `image`, `image_source`, and `image_license` in its frontmatter, and the image file must be physically present at `explore/<slug>.jpg` (or `.png`).

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

The image file lives in the same `explore/` directory as the `.md` file. Add 1–2 seconds of delay between requests to avoid rate limiting.

### Tagging POIs

After creating the neighbourhood files, go through the city's existing sections (`things_to_do/`, `eating_out/`, `bars_and_cafes/`, etc.) and add `neighbourhood: "Exact Title"` to any POI that belongs to a neighbourhood. The title must match the neighbourhood file's `title:` exactly (case-sensitive).

This makes the POI show up on the neighbourhood page automatically without removing it from its section.

### Neighbourhood-local streets, squares, and parks

For each neighbourhood, add POI files for the streets, squares, and parks that give the area its character — the market, the main shopping street, the local park, the canal worth walking. These are stored in `explore/<slug>/` subdirectories and appear **only on the neighbourhood page**, not in city-section listings.

**What belongs here vs in city sections:**

- **City-level** (add to `shopping/`, `bars_and_cafes/`, or `eating_out/` with a `neighbourhood:` tag): only if the street is a genuine destination on its own — a famous market street, a well-known nightlife strip, a park people travel across the city for.
- **Neighbourhood-level only** (store in `explore/<slug>/`): streets, squares, and parks that reward knowing about but are not city-level destinations. A beautiful canal that only locals seek out. A neighbourhood market. A local park. The kind of place that makes a neighbourhood feel like somewhere, not just a location.

**Aim for 3–6 neighbourhood-local POIs per neighbourhood**, covering the full geography — not just one famous street, but the grid of streets and spaces that make the area navigable. Think about what a resident would point a visitor to:

- The park or green space people use daily (e.g. Oosterpark in Oost, Sarphatipark in De Pijp)
- The main commercial artery (e.g. Ferdinand Bolstraat in De Pijp, Kinkerstraat in Oud-West)
- The market, if there is one (e.g. Dappermarkt in Oost, Albert Cuypmarkt in De Pijp — city-level)
- The cross-street or boundary road that defines the neighbourhood's shape (e.g. Ceintuurbaan in De Pijp)
- A quieter canal or side street that gives the area its character (e.g. Bloemgracht in the Jordaan)
- A secondary shopping or restaurant street (e.g. Van Woustraat in De Pijp)

For a neighbourhood like De Pijp, the right coverage is: Albert Cuypmarkt (city-level, in `shopping/`), Ferdinand Bolstraat, Ceintuurbaan, Van Woustraat, and Sarphatipark — five entries that between them describe the shape and character of the neighbourhood. That is the level of detail to aim for.

City-level streets that also belong to a neighbourhood should be added to the relevant city section (`shopping/`, `bars_and_cafes/`, etc.) with `neighbourhood: "Exact Title"` — they will appear in both city listings and the neighbourhood page. Neighbourhood-local POIs go in `explore/<slug>/` only and appear only on the neighbourhood page.

Use `category: "Street"`, `category: "Square"`, or `category: "Park"`. Always include coordinates.

## Cities with sub-locations

Some major cities (Tokyo, London boroughs, etc.) have their districts or wards stored as separate child locations in the hierarchy — e.g. `tokyo/shinjuku.md` with `type: location`. When you encounter this:

1. **Move them into the explore section.** Convert each sub-location to a neighbourhood file in `explore/`, changing `type: location` to `type: neighbourhood`.
2. **Collapse the content.** Merge any content from the sub-location's own sections (things_to_do, eating_out, etc.) into the neighbourhood page body — cite the key POIs inline rather than keeping them as separate files under the old sub-location.
3. **Redirect the old path.** Add a redirect in `redirects.json`: `"old/path/subdistrict" → "city/explore/subdistrict"`.
4. **Delete the old sub-location files.** Remove the `.md` file and its directory once its content has been merged.

The goal is a single canonical city page where neighbourhoods are part of `explore/`, not scattered sub-locations that duplicate the hierarchy.

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
