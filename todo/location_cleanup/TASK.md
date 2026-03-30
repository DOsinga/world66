# Location Cleanup Task

Apply LOCATIONS.md guidelines to every major city in the numbered batch files below.

The Italian cities (Florence, Rome, Venice, Milan, Naples) are already done and serve as reference implementations — see Milan in particular for the `things_to_do` category-filter pattern.

## For each city

1. **Read** the existing location file and all section .md files
2. **Delete** junk sections per LOCATIONS.md:
   - `top_5_must_dos.md`, `budget_travel_idea.md`, `family_travel_idea.md`
   - `practical_informat.md`, `7_day_itinerary.md`, `history_1.md`
   - `festivals.md` (content belongs in `when_to_go`)
   - `books.md`, `cybercafs.md`, `webcams.md`
   - Any duplicates (`nightlife_and_ente.md`, `museums_1.md`, `day_trips_1.md`, etc.)
   - Empty placeholder sections ("We currently have no...")
3. **Fix section titles** — remove city name suffixes:
   - "Bars and Cafes in London" → "Bars and Cafes"
   - "Getting There in Paris" → "Getting There"
4. **Add redirects** in `redirects.json` for any deleted section URLs
6. **Add curated itineraries** per CLAUDE.md — find 2–3 good blog itineraries, create guide entries, add tagged POIs
7. **Review POIs** in existing section directories:
   - Delete spam, junk, or obviously wrong entries (sports venues, gibberish, wrong-country content)
   - Check every POI has `latitude` and `longitude` — add if missing, fix if wrong
   - Verify coordinates are plausible for the city (wrong-country coords are common in old World66 data)
   - Ensure all major sights are covered — if a well-known attraction is missing, add it
   - Update outdated content (prices in lire, defunct businesses) where clearly wrong
   - Add `category` fields to sights POIs if converting to `things_to_do` approach
8. **Commit** as "Update: City Name" — one commit per city

## When to use `things_to_do` vs `sights`

Use the `things_to_do` + category-filter approach (like Milan) when the city has a good mix of museums, architecture, sights, and neighbourhoods and you're creating fresh POIs. Use `sights` (like Florence/Rome/Venice) when the city already has established `sights/` content worth keeping.

See LOCATIONS.md for full detail on both approaches.

## Tracking

When a city is done, add its path (one per line) to `done.txt` in this directory.
This is the source of truth for what has been completed.

```
echo "europe/italy/lazio/rome" >> todo/location_cleanup/done.txt
```

## Batch files

Each file contains 5 cities. Process all 5 in a batch, commit each separately.

### Tier 1 — Major tourist destinations
`batch_00.txt` through `batch_19.txt` cover 100 major world cities.

### Tier 2 — Secondary cities
`batch_20.txt` onwards covers secondary cities. The full list of qualifying
cities can be generated with:
```bash
python3 tools/list_cities.py
```

## Reference implementations

| City | Path | Notes |
|------|------|-------|
| Milan | `europe/italy/lombardia/milan` | `things_to_do` + category filters, full cleanup |
| Florence | `europe/italy/tuscany/florence` | `sights` approach, curated itineraries |
| Rome | `europe/italy/lazio/rome` | `sights` approach, curated itineraries |
| Venice | `europe/italy/veneto/venice` | `sights` approach, curated itineraries |
| Naples | `europe/italy/campania/naples` | `sights` approach, curated itineraries |
