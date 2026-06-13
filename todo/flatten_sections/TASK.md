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
| `books/` | *(skip — books belong inline in books.md, not as POIs)* | — |

Make sure the POI has:
- The correct section tag
- At least one appropriate category tag (if applicable)
- `latitude` and `longitude` — add if missing, verify they are plausible
- A `score` field (float 1.0–10.0) — calibrate against other POIs in the same location

**c. Move it.**
Write the file to `content/<location_path>/<slug>.md` — flat in the location directory, not inside the section subdirectory. If a file with that slug already exists at the flat level, check if it's the same POI. If yes, keep the better version. If no, append `_2` to the slug of the one being moved.

### 3. Ensure the section .md file exists

After moving POIs out, check that a section file exists at `content/<location_path>/<section_slug>.md`. If the section has content worth keeping (there are real POIs for it), create a minimal section file if missing:

```yaml
---
title: "Things to Do"
type: section
---
```

### 4. Delete the now-empty subdirectory

Once all files are moved out, delete the subdirectory. If it still contains files you couldn't move (e.g. images), move those too and then delete.

### 5. Commit

One commit per location:
`Flatten sections: Location Name — N POIs moved`

## What NOT to do

- Do not rewrite POI content unless it is clearly wrong or spam
- Do not add new POIs — this task is structural only
- Do not touch sibling locations (other cities in the same region) — they are separate batch items
- Do not worry about `day_trips/` subdirectories containing location pages rather than POIs — those are handled by the location_cleanup task
