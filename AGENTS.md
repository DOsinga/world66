# World66 — Agent & Developer Guide

## What is this project?

World66 is a restored open-content travel guide. The site is served by Django, reading directly from the filesystem.

## Project structure

```
content/           # All travel guide content (markdown + frontmatter)
guide/             # Django app (models.py, views.py, templates)
static/            # CSS, JS, images, GeoJSON
tools/             # Crawler, extractor, geocoder scripts
world66/           # Django settings
todo/              # Task definitions and batch files for content work
```

## Running the site

```bash
source venv/bin/activate
python3 manage.py runserver 8066
```

## Content structure

`content/` contains a hierarchical world guide. Each item is a markdown file with YAML frontmatter. If an item has children, they live in a directory with the same slug as the file. The hierarchy nests as deep as it needs to: continents contain countries, countries contain regions and cities, cities contain sections, sections contain individual points of interest.

### Images

Pages can have a hero image via frontmatter:

```yaml
image: bars_and_cafes.jpg
image_source: "https://commons.wikimedia.org/wiki/File:Example.JPG"
image_license: "CC BY-SA 4.0"
```

The image file lives alongside the content (in the same directory or the parent directory). Always include `image_source` and `image_license` for attribution.

## Content guidelines

Read these before writing or editing content:

- **[STYLE.md](STYLE.md)** — voice, tone, and writing conventions for all content
- **[CONTINENTS.md](CONTINENTS.md)** — how continent pages should be structured
- **[COUNTRIES.md](COUNTRIES.md)** — how country pages should be structured
- **[LOCATIONS.md](LOCATIONS.md)** — how city/location pages should be structured: section ordering, the `things_to_do` tag-based filter approach, curated itineraries, coordinates, day trips

These documents are the source of truth for their respective content types. If this file and a type-specific doc disagree, the type-specific doc wins.

## The todo system

Ongoing content work is organized in `todo/`. Each subdirectory is a task type:

```
todo/
  country_cleanup/     # Clean up country pages per COUNTRIES.md
    TASK.md            # What to do for each item
    batch_NNN.txt      # ~5 countries to process
    ...
  location_cleanup/    # Structural cleanup of locations per LOCATIONS.md
    TASK.md
    batch_NNN.txt      # 50 locations per batch, sorted largest-first
    ...
  location_enrich/     # Add new content (itineraries, books, stories) to cleaned-up locations
    TASK.md
    ...
```

Each batch file contains a list of content paths to process. The `TASK.md` in each directory describes exactly what to do for each item. Batch files reference the type-specific docs (COUNTRIES.md, LOCATIONS.md) for the detailed rules.

### The `todo` skill

The todo skill can be used to execute a task defined in the todo folder

1. Picks a random shard that doesn't already have a PR
2. Creates a branch: `todo-<task>-<shard>` (e.g. `todo-country_cleanup-batch_00`)
3. Processes each item per TASK.md, committing each separately
4. Deletes the shard file and pushes
5. Creates a PR


## How the rendering works

- `guide/models.py` — filesystem-based content loading. `load_page(path)` finds the markdown file, parses frontmatter, returns a `Page` dataclass.
- `guide/views.py` — single view handles all page types (location, section, poi, etc). Builds sidebar from `children()` which returns `(sections, locations, pois)`.
- `guide/templates/guide/page.html` — unified template, adapts based on `page.page_type`.

The `type` field in frontmatter is the source of truth. Directory filtering in the sidebar uses it: if a directory contains only `poi` type files, it's a section directory (containing POIs), not a sub-location.

## Tabbi MCP Server

The MCP server (`tools/mcp_server.py`) exposes two tools to any MCP-compatible LLM app:

- **`plan_trip`** — creates a trip plan (a `plans/<slug>.md` file) and launches the research agent in the background
- **`search_world66`** — searches the guide for a destination or POI

### Adding to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tabbi": {
      "command": "/path/to/world66/venv/bin/python",
      "args": ["/path/to/world66/tools/mcp_server.py"],
      "env": {
        "W66_BASE_URL": "https://world66.ai",
        "W66_REPO_PATH": "/path/to/world66",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

### Adding to ChatGPT / Gemini

Both support MCP via their tool/function-calling settings. Point them at the same stdio server using the same config format their platform provides.

### The research agent

`tools/research_agent.py` is launched automatically by the MCP server after plan creation. It can also be run manually:

```bash
python tools/research_agent.py \
  --city-path europe/france/midi/cotedazur/marseille \
  --city-title Marseille
```

It requires:
- `ANTHROPIC_API_KEY` — for Claude calls
- `gh` CLI — for opening the PR

The agent reads existing city content, asks Claude for missing notable places, web-searches each one, writes POI `.md` files following `STYLE.md`, commits each file separately, and opens a PR.

### Plan API endpoint

`POST /api/plans/create` — called by the MCP server, also callable directly:

```bash
curl -X POST https://world66.ai/api/plans/create \
  -H "Content-Type: application/json" \
  -d '{"destination":"Marseille","start_date":"2026-07-06","end_date":"2026-07-12"}'
```

Returns `{url, slug, passphrase, city_path, city_title}`.

## Don't

- Don't add accommodation or hotel content (deliberately excluded)
- Don't modify `guide/models.py` to add hardcoded section lists — use the `type` field
- Don't create a database or migrations — the filesystem is the data store
- Don't change the URL structure — it matches the original World66 paths

## Working with Git

- Don't work on main — create a branch for your work. Always branch off `origin/main`, not wherever you happen to be.
- Use worktrees if you are doing multiple things at the same time.
- Try to separate changes to the code from changes to the content from changes to the instruction markdowns — open multiple PRs if needed.
- We squash PRs when they are ready to merge.
- Do not force push. Do not ammend commits

## Software Engineering Practives
- Don't roll your own frontmatter parsing/writing, use the python-frontmatter
- store requirements in requirements.in, compile that using uv to requirements.txt
