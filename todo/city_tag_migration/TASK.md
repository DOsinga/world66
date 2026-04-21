# City Tag Migration Task

The goal of this migration is to change the section folder and neighborhood folders
of cities into tags on the pois of those cities. In the current structure eating_out
pois are usually in the eating_out folder of the city like:

berlin/eating_out/best_kebab.md
berlin/eating_out/decent_kebab.md
berlin/eating_out.md

and for neighborhoods the structure is similar:

berlin/mitte/museum.md
berlin/mitte/park.md
berlin/mitte.md

after this migration we want all pois (best_kebab.md, decent_kebab.md, museum.md, park.md)
all to end up directly in the city root (berlin) but have mitte or eating_out added to
their tags property (a list) in their frontmatter. eating_out.md should already have a
property type=section and mitte a property type=neighborhood, but if not make it so.
if there are no pages for the section or the neighborhood yet, introduce them

## For each city

### 1. Read the city

Scan `content/<city_path>/` — look at all section directories and the POI files inside
them. Understand what sections the city has and which POIs live where.

### 2. Tag each POI

For every POI `.md` file in a section subdirectory, add a `tags:` field that includes:
- The **section slug** it belongs to (e.g. `things_to_do`, `shopping`, `eating_out`, `bars_and_cafes`), 
  based on the folder you find it in, or assign if no folder is available.
- Any **neighbourhood slug** from the existing `neighbourhood:` field — convert it to a
  tag. If a poi is in a neighborhood folder, do the same. Drop the `neighbourhood:` field
  when done. Also drop the `category:` field if present — tags now drive the filter bar.
- Any other relevant cross-cutting tags, indicating aspects of this poi you know, including the type
  of place like restaurant, bar, museum, castle, park etc. Use your best judgment for type tags 
  we'll normalize these in a follow-up pass after seeing what the full distribution     
  looks like.

Example — a restaurant in De Pijp that currently has `neighbourhood: "De Pijp"`:
```yaml
tags: [eating_out, de_pijp, restaurant]
```
- When you are redoing a poi and you notice it is rather empty, feel free to add information you
  know. 

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

### 4. Move the pois

Once correctly annotated, move the pois to the root of the city and delete the now empty section and
neighborhood folders. Make sure you end up with the same number of pois, not counting dupes of course.

### 5. Page layout

Take a good look at the page layout and make sure it's nicely readable. 
E.g. replace markers like ** with the appropriate bold text.

### 6. Image

If the city page does not have an `image:` field in its frontmatter, run the find-photo skill
to find and assign a suitable image before committing. Do not skip this step — every city
must have an image when done.

### 7. Commit

One commit per city: `Tag migration: City Name`

## Rules

- Tag slugs must be lowercase with underscores, matching the section `.md` filename
- A POI can have multiple section tags if it genuinely fits more than one
- Only tag POIs you are confident about — it is better to leave a tag out than add a wrong one
