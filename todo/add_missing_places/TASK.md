# Add Missing Places Task

This task adds new destination pages to World66 for places that Wikivoyage covers but we don't. Each batch file lists 5 paths. For each path, create the destination from scratch.

## Batch file naming

- `top_NNNN.txt` — high-traffic destinations, missing coverage is most damaging
- `med_NNNN.txt` — well-known but niche destinations
- `low_NNNN.txt` — lesser-visited or specialized destinations

## For each path

### 0. Confirm the place is genuinely missing

Before creating anything, verify the location doesn't already exist:

1. Run `find content -iname '<slug>.md'` using the last segment of the path as the slug.
2. Also try no-underscore and diacritic-folded variants: e.g. for `phu_quoc` also try `phuquoc`.
3. If a file is found, verify it's the same place (check coordinates / title).
4. If it already exists, skip this entry — run `python3 tools/mark_done.py add_missing_places <path/to/page.md>` and move on.

### 1. Determine place type

Check the path and decide `loc_type`:
- `city` — a settlement (town, city, village)
- `feature` — a non-settlement attraction with its own page (national park, archaeological site, island, lake)
- `region` — only if the path is clearly a region that will contain city children

### 2. Create the parent directory if needed

If the path is `continent/country/region/city` and `content/continent/country/region/` doesn't exist yet as a directory, the region `.md` file may exist as a flat file only. Create the directory and start adding children. Do not move or delete the existing `.md` file — in World66, a `.md` file and a same-name directory coexist: the `.md` is the region overview and the directory holds its cities.

### 3. Create the main location file

Create `content/<path>.md` with this frontmatter:

```yaml
---
title: City Name
type: location
loc_type: city          # or feature / region
latitude: XX.XXXX
longitude: XX.XXXX
---
```

- **Coordinates**: look up on OpenStreetMap. Use 4 decimal places. Do not invent coordinates.
- **No `done:` field** — leave it out; the enrich task adds it later.
- **No `score:` field** — leave it out.

### 4. Write the overview

3–5 paragraphs for cities; 2–3 for features. Follow STYLE.md:
- Open with what makes the place distinctive
- Paint the picture — character, landscape, highlights
- Be specific, opinionated, honest
- Link to sub-pages that exist

### 5. Create core section files

Always create:
- `content/<path>/things_to_do.md` — required if the place has sights
- `content/<path>/getting_there.md` — how to reach the place

Create where relevant:
- `eating_out.md`, `bars_and_cafes.md` — for towns and cities
- `when_to_go.md` — for places with clear seasons
- `getting_around.md` — for larger cities

Section frontmatter:
```yaml
---
title: Things to Do
type: section
---
```

### 6. Create POI files

Aim for:
- Major destination (capital, world-famous): **20–50 POIs**
- Important city: **10–20 POIs**
- Smaller town or feature: **5–10 POIs, the real highlights**

For each POI:
1. Run `python3 tools/wiki_geosearch.py <lat> <lng> --radius 5000 --limit 25 --json` to find nearby Wikipedia-tagged places
2. Add POIs using coordinates from that output
3. Supplement with your own knowledge for unmapped but well-known places

POI frontmatter:
```yaml
---
title: POI Name
type: poi
tags:
  - things_to_do
  - sight          # or museum, neighbourhood, restaurant, bar, etc.
latitude: XX.XXXX
longitude: XX.XXXX
---
```

For major sights, add a `story:` field (2–4 sentences, specific and surprising).

### 7. Add a hero image

Use the `find-photo` skill. Don't commit without an image for a named destination.

### 8. Mark done

Add to the location's frontmatter:
```yaml
done:
  add_missing_places: 2026-06-05
```

Use today's date, not this fixed date.

### 9. Commit

One commit per location: `Add: City Name`

---

## Notes on specific paths

**`northamerica/mexico/chiapas/palenque`** — `chiapas.md` already exists but there is no `chiapas/` directory. Create the directory and add `palenque.md` inside it. Do not touch the existing `chiapas.md`.

**`southamerica/chile/atacamadesert/san_pedro_de_atacama`** — `atacamadesert/` already exists. Add `san_pedro_de_atacama.md` inside it.

**`asia/indonesia/bali/nusa_penida`** — `bali/` already exists. Add `nusa_penida.md` inside it. `loc_type: feature` (it's an island).

**`asia/indonesia/sulawesi/tana_toraja`** — Sulawesi exists. Add `tana_toraja.md` inside it. `loc_type: region` (Tana Toraja is a regency, not a single town).
