# World66 — Agent & Developer Guide

## What is this project?

World66 is a restored open-content travel guide. The content was crawled from the Wayback Machine and converted to markdown files with YAML frontmatter. The site is served by Django, reading directly from the filesystem — no database.

## Project structure

```
content/           # All travel guide content (markdown + frontmatter)
guide/             # Django app (models.py, views.py, templates)
static/            # CSS, JS, images, GeoJSON
tools/             # Crawler, extractor, geocoder scripts
world66/           # Django settings
```

## Running the site

```bash
source venv/bin/activate
python3 manage.py runserver 8066
```

No database, no migrations. Content changes are live immediately.

## Content format

Every page is a markdown file with YAML frontmatter. There are three types:

### Location (country, city, region)
```yaml
---
title: "Amsterdam"
type: location
latitude: 52.3731
longitude: 4.8924
---

Body text in markdown...
```

File lives at `content/europe/netherlands/amsterdam/amsterdam.md` and is served at `/europe/netherlands/amsterdam`.

### Section (sights, eating out, etc.)
```yaml
---
title: "Eating Out"
type: section
---
```

File lives at `content/europe/netherlands/amsterdam/eating_out.md` and is served at `/europe/netherlands/amsterdam/eating_out`. Sections are always children of a location.

### POI (point of interest)
```yaml
---
title: "Rijksmuseum"
type: poi
address: "Museumstraat 1, 1071 XX Amsterdam"
url: "www.rijksmuseum.nl"
opening_hours: "9:00-17:00 daily"
admission: "€22.50"
---
```

POI files live inside section directories: `content/europe/netherlands/amsterdam/sights/rijksmuseum.md` and are served at `/europe/netherlands/amsterdam/sights/rijksmuseum`.

### Allowed frontmatter properties for POIs
address, phone, url, email, opening_hours, closing_time, price, admission, isbn, author, connections, getting_there, accessibility, zipcode, price_per_night

## Contributing content

Your role is to improve this travel guide. The content was originally written by travelers between 1999 and 2018, then restored from the Wayback Machine. Much of it is outdated. Research destinations and update or add content.

### Workflow

Fork → edit markdown → open a PR.

1. Pick a destination to improve — look for pages with thin or outdated content
2. Research the destination using web search
3. Edit the markdown files in `content/`
4. Commit to a branch and open a PR

### Content guidelines

**Write like a travel guide, not an encyclopedia.** Be practical and opinionated. What should a traveler actually do, see, eat? What should they avoid? Include prices, hours, and addresses where possible.

**Keep it concise.** A good city overview is 3-5 paragraphs. A section (sights, eating out) is 2-4 paragraphs of overview followed by POI entries for specific places.

**Be honest about what's changed.** If a restaurant has closed or an area has changed significantly, say so. Don't preserve outdated information just because it was in the original.

**Use the frontmatter.** Every file needs the correct `type` (location, section, poi) and `title`. POIs should have `address` and any other applicable properties.

**Add coordinates.** Include `latitude` and `longitude` for locations and POIs when you can determine them.

### File structure rules

- Location file: `content/continent/country/city/city.md` (slug matches directory name)
- Section file: `content/continent/country/city/sights.md` (in the location's directory)
- POI file: `content/continent/country/city/sights/some_place.md` (in a section subdirectory)
- Slugs are lowercase with underscores: `eating_out.md`, `some_restaurant.md`
- Don't create accommodation, internet cafe, economy, or senior travel sections

### Example: updating a city

If `content/europe/france/paris/paris.md` has thin content, rewrite it with current information. Then update section files like `sights.md`, `eating_out.md`, and add POIs:

```
content/europe/france/paris/sights/eiffel_tower.md
content/europe/france/paris/sights/louvre.md
content/europe/france/paris/eating_out/le_bouillon_chartier.md
```

### Example: adding a new destination

```bash
mkdir -p content/asia/japan/tokyo/sights
```

Create `content/asia/japan/tokyo/tokyo.md` with `type: location`, then add section and POI files.

### PR expectations

- One destination per PR (or a small set of related destinations)
- Title: "Update: Paris" or "Add: Tokyo"
- Describe what you changed and what sources you used
- Don't modify the Django code, templates, or tools unless specifically asked

## How the rendering works

- `guide/models.py` — filesystem-based content loading. `load_page(path)` finds the markdown file, parses frontmatter, returns a `Page` dataclass.
- `guide/views.py` — single view handles all three types. Builds sidebar from `children()` which returns `(sections, locations, pois)`.
- `guide/templates/guide/page.html` — unified template, adapts based on `page.page_type`.

The `type` field in frontmatter is the source of truth. Directory filtering in the sidebar uses it: if a directory contains only `poi` type files, it's a section directory (containing POIs), not a sub-location.

## Don't

- Don't add accommodation or hotel content (deliberately excluded)
- Don't add internet cafe listings (obsolete)
- Don't modify `guide/models.py` to add hardcoded section lists — use the `type` field
- Don't create a database or migrations — the filesystem is the data store
- Don't change the URL structure — it matches the original World66 paths
