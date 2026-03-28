# CLAUDE.md

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

## How the rendering works

- `guide/models.py` — filesystem-based content loading. `load_page(path)` finds the markdown file, parses frontmatter, returns a `Page` dataclass.
- `guide/views.py` — single `page_view` handles all three types. Builds sidebar from `children()` which returns `(sections, locations, pois)`.
- `guide/templates/guide/page.html` — unified template, adapts based on `page.page_type`.
- No database, no migrations. Content changes are live immediately.

## How type detection works

The `type` field in frontmatter is the source of truth. It is set by `tools/extract_content.py` during extraction:
- If the file's parent directory is a section directory → `poi`
- If the file's name matches a known section slug → `section`
- Otherwise → `location`

Directory filtering in the sidebar uses the type field: if a directory contains only `poi` type files, it's treated as a section directory (containing POIs), not a sub-location.

## Contributing content

The preferred workflow is: fork → edit markdown → open a PR.

When improving a destination:
- Research the location and rewrite the body text with current, accurate information
- Keep the YAML frontmatter format — don't remove existing fields, add where useful
- For new POIs, create a `.md` file in the appropriate section directory
- Set `type: poi` and include address, url, phone where available
- Use `latitude` and `longitude` if you can determine them
- Slugs should be lowercase, no spaces — use underscores

When adding a new destination:
1. Create the directory: `content/continent/country/city/`
2. Create `city.md` with `type: location`
3. Add section files (`sights.md`, `eating_out.md`, etc.) with `type: section`
4. Add POI files in section subdirectories with `type: poi`

## Don't

- Don't add accommodation or hotel content (was deliberately excluded)
- Don't add internet cafe listings (obsolete)
- Don't modify `guide/models.py` to add hardcoded section lists — use the `type` field
- Don't create a database or migrations — the filesystem is the data store
- Don't change the URL structure — it matches the original World66 paths
