# AGENTS.md

Instructions for AI agents contributing to World66.

## Your role

You are improving an open-content travel guide. The content was originally written by travelers between 1999 and 2018, then restored from the Wayback Machine. Much of it is outdated. Your job is to research destinations and update or add content.

## Quick start

1. Pick a destination to improve — look for pages with thin or outdated content
2. Research the destination using web search
3. Edit the markdown files in `content/`
4. Commit to a branch and open a PR

## Content guidelines

**Write like a travel guide, not an encyclopedia.** Be practical and opinionated. What should a traveler actually do, see, eat? What should they avoid? Include prices, hours, and addresses where possible.

**Keep it concise.** A good city overview is 3-5 paragraphs. A section (sights, eating out) is 2-4 paragraphs of overview followed by POI entries for specific places.

**Be honest about what's changed.** If a restaurant has closed or an area has changed significantly, say so. Don't preserve outdated information just because it was in the original.

**Use the frontmatter.** Every file needs the correct `type` (location, section, poi) and `title`. POIs should have `address` and any other applicable properties from this list: address, phone, url, email, opening_hours, closing_time, price, admission, isbn, author, connections, getting_there, accessibility, zipcode, price_per_night.

**Add coordinates.** Include `latitude` and `longitude` for locations and POIs when you can determine them.

## File structure rules

- Location file: `content/continent/country/city/city.md` (slug matches directory name)
- Section file: `content/continent/country/city/sights.md` (in the location's directory)
- POI file: `content/continent/country/city/sights/some_place.md` (in a section subdirectory)
- Slugs are lowercase with underscores: `eating_out.md`, `some_restaurant.md`
- Don't create accommodation, internet cafe, economy, or senior travel sections

## Example: updating a city

If `content/europe/france/paris/paris.md` has thin content:

```yaml
---
title: "Paris"
type: location
latitude: 48.8566
longitude: 2.3522
---

Paris is the capital of France and one of the most visited cities in the world...
```

Then update section files like `sights.md`, `eating_out.md`, and add POIs:

```
content/europe/france/paris/sights/eiffel_tower.md
content/europe/france/paris/sights/louvre.md
content/europe/france/paris/eating_out/le_bouillon_chartier.md
```

## Example: adding a new destination

```bash
mkdir -p content/asia/japan/tokyo/sights
```

Create `content/asia/japan/tokyo/tokyo.md`, `sights.md`, etc.

## PR expectations

- One destination per PR (or a small set of related destinations)
- Title: "Update: Paris" or "Add: Tokyo"
- Describe what you changed and what sources you used
- Don't modify the Django code, templates, or tools unless specifically asked
