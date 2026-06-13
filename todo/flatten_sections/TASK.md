# Flatten Section Directories

## What this fixes

Old World66 content stored POIs inside section subdirectories:

```
city/
  things_to_do/
    cafe.md        ← wrong
    museum.md      ← wrong
  things_to_do.md
```

The correct structure is flat — POIs live alongside the section file, not inside a subdirectory named after it:

```
city/
  cafe.md          ← correct
  museum.md        ← correct
  things_to_do.md
```

See LOCATIONS.md — "POIs always live flat in the city or feature directory — never in a section subdirectory."

## For each location in the batch

### 1. Find section subdirectories

Look for any directories named `things_to_do`, `eating_out`, `bars_and_cafes`, `shopping`, `beaches`, `sights`, `museums`, `nightlife`, `books`, `day_trips` inside the location directory.

### 2. For each POI file in those subdirectories

Read the file. For each one:

**a. Decide whether to keep it.**
Delete if: it's a hotel/accommodation, completely empty, obvious spam, or the same place already exists as a flat sibling POI.

**b. Fix the tags.**
The POI needs a section tag matching the section it belongs in. Map the old subdirectory name to the right section tag:

| Old subdirectory | Section tag | Typical category tags |
|-----------------|-------------|----------------------|
| `things_to_do/`, `sights/` | `things_to_do` | `sight`, `museum`, `architecture`, `neighbourhood` |
| `museums/` | `things_to_do` | `museum` |
| `eating_out/` | `eating_out` | `restaurant` |
| `bars_and_cafes/`, `nightlife/` | `bars_and_cafes` | `bar` |
| `shopping/` | `shopping` | `market` (if a market) |
| `beaches/` | `beaches` | *(no standard category tag)* |
| `books/` | *(special handling — see below)* | — |
| `day_trips/` | *(special handling — see below)* | — |

Make sure the POI has:
- The correct section tag
- At least one appropriate category tag (if applicable)
- `latitude` and `longitude` — add if missing, verify they are plausible
- A `score` field (float 1.0–10.0) — calibrate against other POIs in the same location

**c. Move it.**
Write the file to `content/<location_path>/<slug>.md` — flat in the location directory, not inside the section subdirectory. If a file with that slug already exists at the flat level, check if it's the same POI. If yes, keep the better version. If no, append `_2` to the slug of the one being moved.

### 3. Handle `books/` subdirectories

Books are **not POIs** — they are not points on a map and should not be `type: poi` files. The correct format is 3–5 inline recommendations written directly in `books.md`.

For each file in a `books/` subdirectory:
- Read the content (title, author, description)
- If `books.md` already exists at the flat level, append the book as an inline paragraph: name the book and author, describe what it's about, explain why a traveller would want to read it
- If `books.md` does not exist, create it with those recommendations inline
- Delete all the individual book POI files
- Delete the `books/` subdirectory

Do not create `type: poi` files for books. Do not move book files flat.

### 4. Handle `day_trips/` subdirectories

Day trip entries are **location links**, not POIs. The correct format is a `day_trips.md` section file with a `linked_locations:` list pointing to real location pages in the hierarchy.

For each file in a `day_trips/` subdirectory:
- Check whether it is a `type: location` or `type: poi` file
- If it is a location page (or links to one): find the matching path in `content/` and add it to `linked_locations:` in `day_trips.md`
- If it is a POI with no real location page, it is probably spam — delete it
- Once all entries are processed, delete the `day_trips/` subdirectory

The resulting `day_trips.md` should look like:

```yaml
---
title: Day Trips
type: section
linked_locations:
  - europe/italy/lazio/frascati
  - europe/italy/lazio/ostiaantica
---

Brief overview of day trip options.
```

### 6. Ensure the section .md file exists

After moving POIs out, check that a section file exists at `content/<location_path>/<section_slug>.md`. If the section has content worth keeping (there are real POIs for it), create a minimal section file if missing:

```yaml
---
title: "Things to Do"
type: section
---
```

### 7. Delete the now-empty subdirectory

Once all files are moved out, delete the subdirectory. If it still contains files you couldn't move (e.g. images), move those too and then delete.

### 8. Commit

One commit per location:
`Flatten sections: Location Name — N POIs moved`

## What NOT to do

- Do not rewrite POI content unless it is clearly wrong or spam
- Do not add new POIs — this task is structural only
- Do not touch sibling locations (other cities in the same region) — they are separate batch items
- Do not rewrite POI content beyond fixing tags, coordinates, and scores
