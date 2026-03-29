# Country Cleanup Task

Apply COUNTRIES.md guidelines to every country in the numbered batch files below.

## For each country

1. Read the existing overview and all section .md files
2. **Delete** per COUNTRIES.md:
   - City-level sections at country level (eating_out, bars_and_cafes, nightlife, shopping, museums, day_trips, beaches)
   - Legacy sections (tours_and_excursio, webcams, budget_travel_idea, family_travel_idea, senior_travel_idea)
   - Sights (replaced by highlights)
   - Empty placeholders ("We currently have no...")
   - Spam files (gibberish filenames, wrong-country content, SEO spam)
   - books/ subdirectories with POI entries (books should be inline)
   - Duplicate subdirectories (country/country/)
3. **Rewrite** sections that exist but have poor content:
   - Fix markdown artifacts (`**** **`, `&ldquo;`, `&rsquo;`, `&prime;`)
   - Replace CIA World Factbook data dumps in people.md
   - Replace dead Amazon links in books.md
   - Replace generic/wrong-country content
   - Fix outdated references (defunct airlines, 1990s prices, etc.)
4. **Create** required sections that are missing:
   - `getting_there.md` — how to arrive
   - `getting_around.md` — transport within the country
   - `practical_informat.md` — visas, money, language, safety
   - `when_to_go.md` — climate and seasons
   - `highlights.md` — opinionated "why you'd go" section
5. **Create** optional sections where they add value:
   - `food.md` — always worth having, even for countries without famous cuisine
   - `people.md`, `festivals.md`, `books.md`, `health.md`, `top_5_must_dos.md` — where relevant
6. **Clean up** any other existing sections: fix formatting, tighten writing
7. **Commit** as "Update: Country Name" — do NOT push until reviewed
8. Remove country from its batch file (or delete the batch file when all 5 are done)

## Voice and style

See STYLE.md and COUNTRIES.md. Warm, direct, honest. Second person for advice. Short paragraphs. No marketing speak. Link to existing sub-locations.

## Batch files

Each file contains 5 countries. Process all 5 in a batch, commit each separately.
