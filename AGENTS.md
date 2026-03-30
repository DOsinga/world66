# World66 — Agent & Developer Guide

## What is this project?

World66 is a restored open-content travel guide. The site is served by Django, reading directly from the filesystem

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

## Key documentation

- **[LOCATIONS.md](LOCATIONS.md)** — how to structure a city properly: section ordering, the `things_to_do` category-filter approach, adding POIs from curated itineraries
- **[STYLE.md](STYLE.md)** — voice, tone, and writing conventions

## Contributing content

Your role is to improve this travel guide. The content was originally written by travelers between 1999 and 2018, then restored from the Wayback Machine. Much of it is outdated. Research destinations and update or add content.

**Read [STYLE.md](STYLE.md) before writing.** It defines the voice, tone, and structure of World66 content.

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

## Adding curated itineraries to a city

When asked to "add curated itineraries" for a city, follow these steps exactly.

### What the feature does

Each curated itinerary is a real blog post or travel guide written by someone who knows the city. The World66 entry links out to the original post and adds all the places it mentions as proper POIs — tagged so the tag page aggregates the guide entry and all its places together.

### Step-by-step

**1. Research**
Find 2–3 well-written, specific itineraries for the city (blog posts, travel guides). Prefer posts that name specific restaurants, cafes, sights and bars rather than generic advice. Search for e.g. "one day in Rome itinerary" or "48 hours in Florence blog".

**2. Create the section**
Create `content/{path}/day_guides.md`:
```yaml
---
title: "Curated Itineraries"
type: section
order: 1
---

Curated itineraries for spending time in {City}, drawn from travellers who know it well.
```
`order: 1` makes it appear second in the sidebar (after General), before Sights and Eating Out.

**3. Create the guide entry for each itinerary**
Create `content/{path}/day_guides/{slug}.md` — one file per itinerary. These are POIs within the section:
```yaml
---
title: "One Day in Rome — Walks of Italy"
type: poi
url: "www.walksofitaly.com/blog/rome/one-day-in-rome"
tags: ["One Day in Rome"]
---

A well-paced single-day itinerary from a Rome-based tour company, covering the Colosseum area in the morning, the centro storico at lunch, and the Vatican in the afternoon. Practical and realistic about timing.
```
- The `url` field renders as a clickable link that opens in a new tab
- The tag (e.g. `"One Day in Rome"`) is the key that links the guide to its places — use the same tag on every POI the itinerary mentions
- Keep the description to 2–3 sentences: what makes this guide worth reading, who it's for, what it covers

**4. Add the places as POIs**
For each place the itinerary mentions, check if a POI already exists in the relevant section directory. If it does, add the tag. If it doesn't, create a new POI file in the correct section (`sights/`, `eating_out/`, `bars_and_cafes/`):
```yaml
---
title: "Trattoria da Enzo al 29"
type: poi
address: "Via dei Vascellari 29, Rome"
opening_hours: "Mon–Sat 12:30–15:00, 19:30–23:00; closed Sun"
latitude: 41.889
longitude: 12.472
tags: ["One Day in Rome"]
---

A no-frills Roman trattoria in Trastevere...
```

Make sure the relevant sections exist (`sights.md`, `eating_out.md`, `bars_and_cafes.md`) — create them if not.

**5. Update existing POIs**
If a place already has a POI file, add the new tag to its existing `tags` list rather than creating a duplicate.

**6. Commit and push**
Stage all new and modified files, commit with a message like `Add curated itineraries for {City}`, and push to the working branch.

### Tag naming convention
Use `"One Day in {City}"`, `"48 Hours in {City}"`, `"3 Days in {City}"` etc. — match the itinerary's framing. The tag becomes the URL at `/tags/{tag}`.

### File naming
Slugs from the blog title: `one_day_rome.md`, `48_hours_florence.md`. Lowercase, underscores, no special characters.

## Don't

- Don't add accommodation or hotel content (deliberately excluded)
- Don't add internet cafe listings (obsolete)
- Don't modify `guide/models.py` to add hardcoded section lists — use the `type` field
- Don't create a database or migrations — the filesystem is the data store
- Don't change the URL structure — it matches the original World66 paths
