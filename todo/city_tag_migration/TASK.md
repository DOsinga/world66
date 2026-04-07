# City Tag Migration Task

Convert a city's POIs from the old filesystem-only model to the new tag-based model
introduced in PR #128. After migration, POIs are discoverable by tag, can appear in
multiple sections, and can be reached via virtual URLs like `/city/shopping/albert_cuypmarkt`
even if the file lives elsewhere.

## Background

In the old model a POI's section membership was determined purely by which directory it
lived in. In the new model, POIs carry a `tags:` list and sections collect POIs by
querying for their tag. The new system is fully backward-compatible: untagged POIs still
show up via the legacy directory scan, so migration can happen city by city.

## For each city

### 1. Read the city

Scan `content/<city_path>/` — look at all section directories and the POI files inside
them. Understand what sections the city has and which POIs live where.

### 2. Tag each POI

For every POI `.md` file in a section subdirectory, add a `tags:` field that includes:
- The **section slug** it belongs to (e.g. `things_to_do`, `shopping`, `eating_out`)
- Any **neighbourhood slug** from the existing `neighbourhood:` field — convert it to a
  tag slug (lowercase, underscores). Keep the `neighbourhood:` field for now so PR #105
  content still renders correctly during the transition.
- Any other relevant cross-cutting tags (e.g. `outdoor`, `free_entry`) if obvious

Example — a restaurant in De Pijp that currently has `neighbourhood: "De Pijp"`:
```yaml
tags: [eating_out, de_pijp]
```

### 3. Create neighbourhood pages (for cities that have them)

If the city has neighbourhood content (POIs tagged with district names), create a
neighbourhood page for each district at the city level:

```
content/<city_path>/<neighbourhood_slug>.md
```

```yaml
---
title: "De Pijp"
type: neighbourhood
---

Brief intro to the neighbourhood.
```

If there are 3+ neighbourhoods, also create a `neighbourhoods.md` section_group:

```yaml
---
title: "Neighbourhoods"
type: section_group
groups: neighbourhood
---
```

### 4. Create theme pages (optional, for cities that warrant it)

If you can identify 2+ meaningful cross-cutting themes with enough POIs to support them,
create theme pages at the city level (e.g. `street_art.md`, `lgbtq.md`, `cold_war.md`).
Only do this if it adds genuine value — don't force themes.

### 5. Commit

One commit per city: `Tag migration: City Name`

## Rules

- Do NOT move any files — tags are additive, file locations stay the same
- Do NOT remove the `neighbourhood:` field from POIs yet (needed for PR #105 compat)
- Tag slugs must be lowercase with underscores, matching the section `.md` filename
- A POI can have multiple section tags if it genuinely fits more than one
- Only tag POIs you are confident about — it is better to leave a tag out than add a wrong one

## Batch files

Each batch file lists ~3–5 city paths. Process all cities in a batch, one commit per city.
