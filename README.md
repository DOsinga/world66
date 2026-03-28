# World66 — the travel guide you write

Twenty-five years ago, World66 launched as one of the first open-content travel guides on the internet. The tagline was simple: *the travel guide you write*. Thousands of travelers contributed articles about destinations around the world, all licensed under Creative Commons.

The site was acquired, then shut down. But the content survived in the Wayback Machine.

This project restores World66 from those archives — and reimagines it for the age of AI. What was once *the travel guide you write* is now **the travel guide your agent writes**. Fork the repo, point your AI agent at a destination, and open a PR. The content is markdown with YAML frontmatter. It's that simple.

## Getting started

```bash
# Clone and set up
git clone https://github.com/DOsinga/world66.git
cd world66
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the site
python3 manage.py runserver 8066
# Open http://localhost:8066
```

The site reads directly from the `content/` directory — no database needed. Every page is a markdown file.

## Content structure

Content lives in `content/` organized by geography:

```
content/
├── europe/
│   ├── europe.md                  # Continent overview
│   ├── netherlands/
│   │   ├── netherlands.md         # Country overview
│   │   └── amsterdam/
│   │       ├── amsterdam.md       # City overview
│   │       ├── sights.md          # Section
│   │       ├── eating_out.md      # Section
│   │       └── sights/
│   │           └── rijksmuseum.md  # Point of interest
```

Each markdown file has YAML frontmatter:

```yaml
---
title: "Amsterdam"
type: location          # location, section, or poi
latitude: 52.3731
longitude: 4.8924
---

Amsterdam is the capital of the Netherlands...
```

POIs can have structured properties:

```yaml
---
title: "Rijksmuseum"
type: poi
address: "Museumstraat 1, 1071 XX Amsterdam"
url: "www.rijksmuseum.nl"
opening_hours: "9:00-17:00 daily"
---
```

## Contributing with an AI agent

The easiest way to contribute is to have an AI agent improve or add content:

1. **Fork** the repo on GitHub
2. **Clone** your fork locally
3. **Pick a destination** — find a location page that's thin or missing
4. **Have your agent rewrite it** — ask your AI to research the destination and update the markdown, keeping the frontmatter format
5. **Commit and push** to a branch on your fork
6. **Open a PR** back to `DOsinga/world66`

Example prompt for your agent:

> Look at `content/europe/netherlands/amsterdam/eating_out.md`. Research the current restaurant scene in Amsterdam and rewrite this section with up-to-date information. Keep the YAML frontmatter format. Add POI files for notable restaurants in `content/europe/netherlands/amsterdam/eating_out/`.

### Adding a new destination

Create the directory structure and markdown files:

```bash
mkdir -p content/asia/japan/tokyo/sights
```

Then create `content/asia/japan/tokyo/tokyo.md`:

```yaml
---
title: "Tokyo"
type: location
latitude: 35.6762
longitude: 139.6503
---

Your content here...
```

## Tools

The `tools/` directory contains the scripts used to restore and enrich the content:

| Script | Purpose |
|--------|---------|
| `crawl_inventory.py` | Query the Wayback Machine CDX API for archived URLs |
| `filter_inventory.py` | Filter to content pages, normalize section names |
| `download_pages.py` | Download HTML pages (resumable) |
| `extract_content.py` | Convert HTML to markdown with frontmatter |
| `geocode.py` | Geocode locations using Nominatim/OpenStreetMap |
| `apply_geocodes.py` | Write lat/lng into markdown frontmatter |
| `download_images.py` | Download content images (separate pass) |

## License

All World66 content is licensed under [Creative Commons Attribution-ShareAlike 1.0](https://creativecommons.org/licenses/by-sa/1.0/).

Originally created by [Oberon Medialab](https://oberon.nl) in 1999. Restored from the [Wayback Machine](https://web.archive.org/web/*/world66.com) in 2026.
