# City Restructure Task

Apply LOCATIONS.md guidelines to every city in the numbered batch files below.

## For each city

1. Read the existing location file and all section/POI files
2. **Migrate sights and museums** to `things_to_do/`:
   - Create `things_to_do.md` section file
   - Move POIs from `sights/` and `museums/` into `things_to_do/`
   - Add `category: "Sight"` or `category: "Museum"` to each POI
   - Delete old `sights.md`, `museums.md` section files and directories
3. **Merge nightlife** into `bars_and_cafes/`:
   - Move any worthwhile POIs; delete outdated ones
   - Delete `nightlife.md` and directory
4. **Clean up junk sections**: delete `top_5_must_dos.md`, `budget_travel_idea.md`, `family_travel_idea.md`, `cybercafs.md`, `webcams.md`, duplicates
5. **Add coordinates** to every POI that lacks them; fix wrong coordinates
6. **Add `story:` fields** to 3–5 major sights where you know a good anecdote
7. **Add books section** with 3–5 novels/literature about the city
8. **Create missing sections**: `when_to_go`, `getting_there`, `getting_around` if absent
9. **Add redirects** in `redirects.json` for all old URLs
10. **Commit** as "Restructure: City Name" — do NOT push until reviewed

## Voice and style

See STYLE.md and LOCATIONS.md. Practical, opinionated, concise.

## Batch files

Each file contains 5 cities. Process all 5 in a batch, commit each separately.
