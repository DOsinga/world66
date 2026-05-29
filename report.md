# World66 Site Structure Report

## Overview

The site serves ~51,800 markdown files organized in a filesystem hierarchy:
**Continent > Country > Region/City > Section/POI**

Content is loaded from `content/` with YAML frontmatter classifying pages as `location`, `section`, or `poi`. The three-level display is: locations get listed as sub-destinations, sections appear in the sidebar, and POIs appear under their parent section.

---

## 1. Duplicate Locations (Every Country Listed Twice)

**Severity: High — visible on every page**

Almost every country appears **twice** in its continent's listing. For example, on `/europe`, Albania, Andorra, Armenia, etc. all show 2x. Same on `/africa`, `/southamerica`, etc.

**Root cause:** The `children()` method in `models.py` picks up both the `.md` file (e.g., `albania.md`) AND the directory (e.g., `albania/`) as separate location entries. When both exist, the country appears twice.

This affects 47 out of 52 unique European country URLs, and similar ratios for other continents.

---

## 2. The `content/world/` Duplication

**Severity: High — 5,765 duplicate files**

There are two parallel content trees:
- `content/europe/netherlands/amsterdam/...` (primary, ~46k files)
- `content/world/europe/netherlands/amsterdam/...` (legacy, ~5.8k files)

The `world/` directory appears as its own "continent" on the homepage with links to `/world/africa`, `/world/europe`, etc. — creating a shadow copy of the entire site structure. This `world/` tree is from the original World66 URL scheme (`world66.com/world/europe/...`) and should either be merged into the main tree or excluded.

---

## 3. Section-like Pages Classified as Locations

**Severity: Medium — pollutes destination listings**

Several section-type pages are typed as `location` instead of `section`, causing them to appear in the "Destinations" list instead of the sidebar:

| Slug | Appears as | Should be |
|------|-----------|-----------|
| `health` | "Sights" (wrong title too) under Africa, South America | Section |
| `books` | Shows in destination list at continent level | Section |
| `books_1`, `books_2` | Duplicate "Books" entries under Africa | Section (or merged) |
| `day_trips` | "Day Trips in Asia" in Asia's destination list | Section |
| `eating_out` | "Eating Out in Asia" in destination list | Section |
| `food` | Shows as destination under Asia, Middle East | Section |

The Asia continent page is particularly bad — its destination list includes: Books, Day Trips, Eating Out, Food, alongside actual countries like Cambodia and Vietnam.

---

## 4. Naming Inconsistencies (Duplicate Sections with Different Slugs)

**Severity: Medium — causes duplicate sidebar entries and broken navigation**

The same section concept appears under different slug names:

| Concept | Slugs found | Count |
|---------|------------|-------|
| Nightlife | `nightlife.md` (299), `nightlife_and_ente.md` (526), `nightlifeandente/` (51 dirs) | 3 variants |
| Eating Out | `eating_out.md`, `eatingout/` directory | 2 variants |
| Getting There | `getting_there.md`, `gettingthere/` directory | 2 variants |
| Getting Around | `getting_around.md`, `gettingaround/` directory | 2 variants |

When both variants exist in the same location (e.g., Amsterdam has both `eating_out.md` and `eatingout/`), users see duplicate entries. Found dozens of locations with this overlap.

---

## 5. Asia's Sub-region Nesting Hides Major Countries

**Severity: High — India, Japan, Thailand etc. unreachable from /asia**

Asia uses sub-regions (Middle East, South Asia, South-East Asia, North-East Asia) as an extra hierarchy level. This means:

- `/asia/india` → 404 (actual path: `/asia/southasia/india`)
- `/asia/japan` → 404 (actual path: `/asia/northeastasia/japan`)
- `/asia/thailand` → 404 (actual path: `/asia/south/thailand`)
- `/asia/indonesia` → 404 (actual path: `/asia/southeastasia/indonesia`)

All 12 tested major Asian countries returned 404 at the expected path. Users must know to navigate through the sub-region first. No other continent uses this pattern — Africa lists countries directly, Europe lists countries directly.

The sub-region "South" (`/asia/south`) is particularly confusing as it contains Thailand, Philippines, and Malaysia — which are Southeast Asian countries.

---

## 6. Caribbean/Central America Structural Mess

**Severity: Medium**

Multiple overlapping hierarchies:
- Countries appear **both** directly under `centralamericathecaribbean/` AND under `centralamericathecaribbean/thecaribbean/`
  - Bahamas: 45 files at top level, 12 files under `thecaribbean/`
  - Belize, Costa Rica, El Salvador, Guatemala, Nicaragua, Panama all duplicated
- A typo directory `theccribbean/` exists alongside `thecaribbean/` (contains Dominican Republic)
- Mexico appears under **both** `centralamericathecaribbean/` (41 files) and `northamerica/` (566 files)

---

## 7. Ugly/Unformatted Display Names

**Severity: Low-Medium — looks unpolished**

Several names display as raw slugs without proper formatting:
- "Australiaandpacific" (should be "Australia & Pacific" or "Oceania")
- "Southamerica" (should be "South America")
- "Northamerica" (should be "North America")
- "Frenchsouthernandantarcticlands" (should be "French Southern and Antarctic Lands")
- "Equatorialguinea" (should be "Equatorial Guinea")
- "Czechrepublic" (should be "Czech Republic")

The nav bar already fixes some of these (shows "Oceania" for australiaandpacific) but the continent cards on the homepage and breadcrumbs show the raw slugs.

---

## 8. Spam/Junk/Placeholder Pages

**Severity: Low-Medium — 1,182+ junk files**

Remnants of the wiki-era vandalism and test pages:
- Random strings: `fhBrsdPfsB`, `PzHrTfqApHsCgfyQ`, `yuioplo`, `eaczkqugztsvdfqxig`
- Placeholder pages: "Add a City", "New City", "name of the place", "Town in Haiti"
- Misplaced content: Hanoi hotel under Italy's "Add a City", Buenos Aires under Haiti
- Duplicate scrape artifacts: 1,182 files with `_1`, `_2` etc. suffixes (e.g., `hotels_in_golem.md` through `hotels_in_golem_4.md`)
- "bootyville" (twice) under Honduras
- "Vianen" (a Dutch city) nested under Amsterdam
- "Kihikihi" (a New Zealand town) under Netherlands
- "Webcams & 360 degree pics" pages (12 total) with no actual content

---

## 9. Duplicate Locations Within Countries

**Severity: Medium**

Several locations exist at multiple levels within their country:

**Italy:**
- `sardinia/` (113 files) AND `sardegnasardinia/` (separate entry, 0 extra files) — same island, two entries
- `firenze/` AND `tuscany/florence/` — same city
- `positano/` at country level (should be under Campania)
- `capri/` at country level AND referenced under Campania

**France:**
- `tours.md` AND `tours_1.md` at country level, plus `centre/loirevalley/tours/`
- `bordeaux` appears under `midi/aquitaine/`, `wine/`, AND `aquitaine/`
- `normandy/` AND `normandybrittany/` as separate regions
- `orange.md` at country level AND under `midi/provence/orange`
- `midi/` AND `midi_1/` as separate entries

**Europe:**
- `serbia/`, `montenegro/`, AND `serbiaandmontenegro/` all exist as separate countries (the last is a historical artifact)

---

## 10. Geographic Misplacements

**Severity: Medium**

- **Maldives** listed under Africa (should be Asia)
- **Turkey** only under Asia/Middle East — many would expect it under Europe too
- **Cyprus** only under Asia/Middle East
- **South Sudan** missing entirely (became independent 2011, after most content was written)
- **Kosovo** missing entirely
- **"Health"** pages under Africa and South America are typed as `location` with title "Sights" and nonsensical coordinates

---

## 11. The `content/world/` Shadow Site

The `/world` path creates a parallel navigation structure:
- `/world/about` — site about page (useful, but orphaned)
- `/world/europe` → duplicates `/europe`
- `/world/africa` → duplicates `/africa`
- `/world/takeaway` — historic "take it away" page
- `/world/travelwise` — travel tips section
- `/world/tmp` — titled "World" (leftover temp file)

The `about` and `travelwise` content may be worth preserving but should be moved to a proper location.

---

## 12. Imported Page Chrome / Old Site Mechanism Fragments in Content

**Severity: High — affects ~14,500 files (28% of all content)**

The HTML-to-markdown import captured various pieces of the old World66 page template and mechanism text as body content. These are not travel content — they're navigation elements, footers, attribution blocks, and UI prompts from the original site that got baked into the markdown.

### 12a. Site tagline as body text (4,095 files)

The old page header tagline got imported as the first line of body text:

> The best resource for sights, hotels, restaurants, bars, what to do and see

Present in 4,095 files, always at the start of the body. In 415 of those files, this tagline (plus other boilerplate) is essentially the **only** content — the actual travel information is empty or just a word or two.

### 12b. Page generation timestamp (4,095 files)

The server-side footer timestamp was captured:

> Page last generated on Tue 22:00

Sometimes followed by a stray HTML comment closer `-->`. The `-->` appears in 4,387 files.

### 12c. Wikitravel cross-promotion (3,964 files)

A link to Wikitravel that was part of the page template:

> Additional travel guides are available in ten languages at [**Wikitravel.org**](http://wikitravel.org)

### 12d. Attribution boilerplate (2,232 files)

An italicized attribution line from the old CMS:

> *Part or or all of this text stems from the original article at: [source]*

The "source" is often just a username, a random string, or a page number (e.g., "180").

### 12e. Change history / contributor logs (2,670+ files)

The edit history from the old wiki was imported as body text. Various formats:

```
**Change history**
Orginal article by [RichardOsinga](/member/richardosinga) on 26 April 05
```

```
#### Contributors
September 22, 2006 change by [giorgio](/member/giorgio)
```

```
by [africaguide](/member/africaguide)
August 26, 2010 new by [kieran_m](/member/kieran_m)
```

About 10,673 files contain `/member/` links (which are dead — there's no member system). Of those, ~8,900 are attribution lines like `by [username](/member/xxx)` and ~1,200 are full date-stamped change log entries.

### 12f. "Subsections" navigation blocks (632 files)

The old site had a rendered list of sub-categories that got imported as a markdown section:

```markdown
## Subsections

[Churches](/europe/france/paris/sights/churches)
[Landmarks](/europe/france/paris/sights/landmarks)
[Museums](/europe/france/paris/sights/museums)
```

These are navigation elements, not content. The site already renders sub-pages dynamically via `children()` / POI listing, so these duplicate the navigation.

### 12g. Spam pages (37+ complete spam articles)

Entire spam pages (Moncler jacket store, replica watches, Louis Vuitton ads) were imported as travel content. These include full e-commerce HTML converted to markdown — product descriptions, shopping carts, CSS rules, currency selectors, navigation menus. Examples:
- `cheap_moncler_ange.md` under New Zealand
- `moncler_men_2014_b.md` under Australia
- `replica_ladies_wat.md` under Bali
- `replica_chronograp.md` under India
- `basudev_swain.md` under New York shopping (contains CSS)

### 12h. BBCode fragments (9 files)

Some pages contain raw BBCode that was never rendered:

```
[url=http://example.com]My homepage[/url]
```

### Summary of artifact counts

| Artifact | Files affected |
|----------|---------------|
| `/member/` links (dead) | 10,673 |
| Attribution lines (`by [user]`) | 8,897 |
| Site tagline in body | 4,095 |
| `-->` stray comment closers | 4,387 |
| Page generation timestamp | 4,095 |
| Wikitravel cross-promotion | 3,964 |
| Change history blocks | 2,670 |
| Attribution boilerplate | 2,232 |
| Date-stamped change logs | 1,229 |
| Contributors heading | 1,145 |
| Subsections navigation | 632 |
| Social/interaction UI text | 50 |
| E-commerce spam pages | 39 |
| BBCode fragments | 9 |
| **Files with ≥1 artifact** | **~14,534** |

All of these can be stripped with regex-based cleanup since the patterns are consistent.

---

## Summary of Priorities

1. **Fix the double-listing bug** — every country showing twice (code fix in `children()`)
2. **Strip imported page chrome from content** — tagline, timestamps, Wikitravel links, change history, member links, attribution boilerplate (~14.5k files, all regex-cleanable)
3. **Exclude or merge `content/world/`** — eliminate the shadow content tree
4. **Fix Asia's sub-region nesting** — make India, Japan, etc. directly accessible
5. **Clean up section/location type misclassifications** — especially at continent level
6. **Merge naming variants** — `nightlife` vs `nightlife_and_ente`, `eatingout` vs `eating_out`
7. **Fix display names** — proper formatting for compound slugs
8. **Remove spam and junk pages** — Moncler ads, random strings, placeholders, numeric-suffix duplicates
9. **Resolve geographic duplicates** — Caribbean restructuring, Italy region overlaps
10. **Fix geographic misplacements** — Maldives, Kihikihi, etc.
