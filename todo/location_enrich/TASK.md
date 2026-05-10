# Location Enrich Task

Bring cleaned-up location pages up to the full standard for their tier. This task assumes the location already has the right section structure — if it still has `sights/` or junk sections, run `location_cleanup` first.

## Prerequisites

Before processing a location, verify its frontmatter contains `done: location_cleanup`. If it doesn't, skip it.

---

## Step 0: Classify the location

Add a `tier:` field and descriptive `tags:` to the location's frontmatter:

```yaml
tier: 1         # 1, 2, 3, or 4 — see table below
tags: [culture, museums, beaches]   # whatever applies
```

**Tiers:**

| Tier | Description | Examples |
|------|-------------|---------|
| `1` | Major city — top ~100 globally, visited by millions | NYC, Paris, Tokyo, Bangkok, Florence, Montreal |
| `2` | Second-tier city — top ~1000, meaningful travel destination | Porto, Ghent, Chiang Mai, Cartagena, Queenstown |
| `3` | Third-tier city — top ~5000, regional centre or niche destination | Guysborough, Ellsworth, Atenas |
| `4` | Everything else — small village, suburb, minor stop | One paragraph overview is enough |

**Location tags** (add whichever apply):
`culture`, `museums`, `beaches`, `skiing`, `nightlife`, `food`, `nature`, `history`, `architecture`, `hiking`, `diving`, `wildlife`

---

## Step 1: Convert sublocations to neighbourhoods (where relevant)

If the location has child directories that are neighbourhoods (urban districts of the city, not independent towns or cities), convert them:

- Create a neighbourhood POI in `things_to_do/` with `tags: [things_to_do, neighbourhood]`
- Tag all POIs in that neighbourhood with the neighbourhood's slug (e.g. `tags: [eating_out, montmartre]`)
- Add `neighbourhood: Name` display field to those tagged POIs
- Delete the old sublocation directory

Do **not** convert independent cities, towns, or day-trip destinations — only urban districts that are part of the city.

---

## Step 2: Enrich content by tier

### Tier 1 — Major cities

**things_to_do** (aim for 25–50 POIs):
- Sights, museums, squares, parks, zoos, amusement parks, activities
- Add a `story:` field to the most important ones — a specific anecdote that brings the place to life (2–4 sentences, web-searched and verified)
- Tag each POI: `sight`, `museum`, `park`, `architecture`, `neighbourhood`, etc.

**eating_out** (aim for 10–25 POIs):
- Famous restaurants (Noma in Copenhagen)
- Restaurants/stalls well-known for a local speciality dish
- Streets or squares with diverse restaurants or food stalls
- Food markets, night markets

**bars_and_cafes** (aim for 10–25 POIs):
- Famous cafes (Les Deux Magots in Paris)
- Bars unique to the city (Cheshire Cheese in London)
- Clubs with a reputation (Berghain in Berlin)
- Local specialities (jazz clubs in New Orleans, karaoke bars in Tokyo)
- Streets or squares with many bars and cafes

**shopping** (aim for 5–15 POIs):
- Major shops that are a sight in themselves
- Historic arcades
- Famous markets
- Major shopping streets (deserve a longer write-up)
- Streets or areas with specialty shops

**beaches** — only if the city itself has them

**Write-ups without POIs** (create these sections if absent):
- `getting_there.md`
- `getting_around.md`
- `when_to_go.md` — include major festivals and events worth timing a visit around
- `books.md` — 3–5 novels, not travel guides. Each book is a POI in `books/` with `author:` and `isbn:`.
- `history.md` — only if the city has significant history worth a standalone write-up

**Day trips** — use `day_trips.md` with `linked_locations:` pointing to real location pages. Do not create POIs for day trip destinations.

---

### Tier 2 — Second-tier cities

**things_to_do** (aim for 5–10 POIs):
- The essential sights, museums, squares, parks, activities
- Add `story:` to the 1–2 most important

**eating_out** — add POIs only when genuinely notable (a famous restaurant, an unmissable local dish, a great market). Otherwise write-up only.

**bars_and_cafes** — add POIs only when genuinely notable. Otherwise write-up only.

**Write-ups without POIs** (create if absent and city warrants them):
- `getting_there.md`
- `getting_around.md`
- `when_to_go.md` — include festivals
- `beaches.md` — only if on the sea
- `shopping.md` — write-up only, no POIs needed

**Books** — 3–5 novels if strong candidates exist. Skip if nothing notable.

---

### Tier 3 — Third-tier cities

Write-ups only (no POI lists needed):
- `things_to_do` section body — what to see and do, in prose
- `eating_out` section body — where to eat, in prose
- `bars_and_cafes` section body — if relevant
- `getting_there.md`

No books section needed unless something exceptional exists.

---

### Tier 4 — Everything else

A single well-written overview paragraph. No sections needed unless there is genuinely something specific worth saying.

---

## Step 3: Hero image

If the location file has no `image:` field, use the `find-photo` skill to find and assign a Wikimedia Commons photo.

---

## Step 4: Mark done

Add to the location's frontmatter:

```yaml
done:
  location_cleanup: '...'   # already present
  location_enrich: 'YYYY-MM-DD'
tier: 1
tags: [culture, museums]
```

---

## Step 5: Commit

One commit per location: `"Enrich: City Name"`

---

## Rules

- **Every POI must have `latitude` and `longitude`.** Do not publish a POI without coordinates.
- **Verify coordinates are correct.** Look up each POI by name and cross-check the lat/lng against a map. Wrong-country and wrong-city coordinates are common in old World66 data. A museum in Berlin should not have coordinates in Texas. If you cannot verify coordinates confidently, leave the POI out rather than publishing bad data.
- **Use web search for all facts.** Never invent details, stories, or book titles.
- **Quality over completeness.** A great overview with 10 well-written POIs beats a thin list of 40.
- **Don't force sections.** Only create a section if you have real content for it.
- **Day trips are links, not POIs.** Use `linked_locations:` in `day_trips.md`.
- See STYLE.md and LOCATIONS.md for voice, tone, and detailed formatting rules.
- See LOCATIONS.md for reference implementations (Rome, Florence, Milan).

## Batch files

Each file contains ~5 locations, sorted highest content score first (most-visited destinations first).
