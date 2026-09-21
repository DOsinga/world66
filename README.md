# World66 — the travel guide you write

Twenty-five years ago, World66 launched as the first open-content travel guide on the internet — and one of the first wikis where anyone could edit any page, two years before Wikipedia.

The tagline was simple: *the travel guide you write*. 
Thousands of travelers contributed articles about destinations around the world, all licensed 
under Creative Commons.

The site was acquired, then shut down. But the content survived in the Wayback Machine.

This project restores World66 from those archives — and reimagines it for the age of AI. 
What was once *the travel guide you write* is now **the travel guide your agent writes**. 
Fork the repo, point your AI agent at a destination, and open a PR. 
The content is markdown with YAML frontmatter. It's that simple.

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
│   │       ├── things_to_do.md          # Section
│   │       ├── eating_out.md      # Section
│   │       └── rijksmuseum.md      # Point of interest (POI) linked to the things to do section by its tags
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

## Contributing with the /todo skill

If you're using [Claude Code](https://claude.com/claude-code) (or another agent that supports skills), the fastest way to contribute is with the built-in `/todo` skill.

The `todo/` directory contains batched tasks — things like cleaning up country pages, adding missing sections, or fixing outdated content. Each task has a `TASK.md` explaining what to do and `.txt` shard files listing the items to process.

To get started:

```bash
# Clone, set up, and run the site
git clone https://github.com/DOsinga/world66.git
cd world66
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 manage.py runserver 8066

# Make sure gh (GitHub CLI) is installed and authenticated
brew install gh  # if needed
gh auth login    # if needed

# Then just tell your agent:
/todo
```

Running `/todo` without arguments shows the available tasks. Running `/todo country_cleanup` (for example) picks a random batch, processes all items, and opens a PR. One batch = one PR. The agent handles everything: reading the task description, making the changes, committing, pushing, and creating the PR.

You can also contribute manually — see the section above.

## Tools

The `tools/` directory contains the scripts used to restore and enrich the content:

| Script | Purpose |
|--------|---------|
| `geocode.py` | Geocode locations using Nominatim/OpenStreetMap |
| `apply_geocodes.py` | Write lat/lng into markdown frontmatter |
| `download_images.py` | Download content images (separate pass) |

## Deployment

The live site runs on `world66.ai` under a systemd unit called `world66`, served by
uvicorn from a unix socket.

**Use the virtualenv inside the site directory**, not the one in the home directory —
that belongs to another site on the same box and is on Python 3.9, which cannot run
this codebase (`passport_app/scenarios.py` uses `list | None`, which needs 3.10+).

```bash
cd ~/sites/world66
source venv3/bin/activate          # NOT ~/venv3
```

### Deploying a change

```bash
cd ~/sites/world66 && git pull origin
venv3/bin/python manage.py collectstatic --noinput
venv3/bin/python indexer.py                        # rebuilds search.db
sudo systemctl restart world66
```

Calling `venv3/bin/python` directly rather than activating first is the more reliable
form in scripts and cron, where `source` is often unavailable.

**The restart is only needed for code changes** — anything touching `guide/`,
`world66/`, `passport_app/` or the templates. Content under `content/` is read from
disk per request, so a pull is enough. `collectstatic` matters when `static/` changed;
`indexer.py` when content changed.

### Checking on it

```bash
sudo systemctl status world66 --no-pager
sudo journalctl -u world66 -n 50 --no-pager
systemctl cat world66                  # unit definition, including the environment
```

Secrets (`DJANGO_SECRET_KEY`, `CARTO_BASEMAP_KEY`, `GITHUB_TOKEN`) live as `Environment=`
lines in that unit, so `systemctl cat` prints them — redact before pasting anywhere.
Edit them with `sudo systemctl edit --full world66`, then `daemon-reload` and restart.

`DJANGO_SECRET_KEY` is worth treating carefully: besides sessions, `guide/views.py` uses
`django.core.signing` with it, so anyone holding it can forge signed form tokens. Rotate
with:

```bash
venv3/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Running the dev server on the box

```bash
venv3/bin/python manage.py runserver 8066
```

Useful for a quick check, but it is Django's development server — single-threaded and
not meant to face traffic — and port 8066 may already be busy. Note that the first
city-page request builds an index across the whole content tree and takes minutes;
warm it with one request and wait rather than assuming it has hung.

## License

All World66 content is licensed under [Creative Commons Attribution-ShareAlike 1.0](https://creativecommons.org/licenses/by-sa/1.0/).
