# Continent Pages — Guidelines

Continent pages are the front doors to huge parts of the world. They should make travelers excited and help them decide where to go. This document describes what a good continent page looks like and what sections should accompany it.

## The overview page (`africa.md`, `europe.md`, etc.)

The overview is 5–10 paragraphs. It should do three things:

### 1. Set the mood

Open with one or two lines that capture what makes this continent distinctive as a travel destination. Not a geography textbook opener — a traveler's impression.

Good: *"South America is salsa, cumbia, samba and tango. Life really swings there."*
Bad: *"South America is the fourth largest continent, with an area of 17.84 million km²."*

### 2. Walk through the regions

The bulk of the overview is a geographic tour. Group countries into natural regions and describe what each region offers travelers. For each region:

- Name the countries and link to them
- Mention 2–3 specific highlights (cities, parks, ruins, landscapes)
- Give a sense of the travel experience: is it easy or rough, expensive or cheap, crowded or empty
- Include something honest or surprising — political realities, safety, how tourism has changed

Move geographically (north to south, or however it makes sense). The reader should come away with a mental map.

### 3. Help the reader choose

The overview should function as a decision tool. A traveler who reads it should know: "I want beaches → go here. I want ancient history → go there. I want adventure off the beaten track → try this."

Don't just list countries — characterize them. What kind of trip does each offer?

## Sections at the continent level

Continent pages should have sections that address continent-wide practical concerns. Not every section makes sense for every continent, but here's the standard set:

### ~~Getting There (`getting_there.md`)~~ — Skip

Getting there doesn't make sense at the continent level — people fly to countries, not continents. This information belongs on country pages. Don't create continent-level getting_there sections; existing ones can be removed.

### Getting Around (`getting_around.md`)

How do you travel within the continent? Keep it brief and high-level: what are the main options for crossing borders and covering long distances (bus networks, trains, domestic flights, rental cars)? What's easy, what's hard? Don't duplicate country-level transport details — just give the big picture so a traveler can plan a multi-country route.

### Practical Information (`practical_informat.md`)

Continent-wide practicalities that apply broadly:

- **Visas** — regional visa schemes (Schengen, EAC, ECOWAS), which countries are easy/hard to enter
- **Money** — shared currencies (Euro, CFA franc), ATM availability, whether cash or card is king
- **Languages** — what languages you'll encounter, how far English gets you
- **Safety** — general patterns, not country-by-country (that belongs on country pages)
- **Connectivity** — mobile coverage and SIM card availability, Wi-Fi patterns
- **Climate overview** — when is best to visit different parts of the continent

### Health (`health.md`)

Only for continents where health is a major travel planning concern (Africa, South America, parts of Asia). Vaccinations commonly needed, malaria zones, water safety, altitude considerations. Link to country pages for specifics.

### ~~Beaches (`beaches.md`)~~ — Skip

Beach information belongs on country and city pages, not at the continent level. Don't create continent-level beaches sections; existing ones can be removed.

### People (`people.md`)

The human landscape of the continent. Ethnic and cultural diversity, languages spoken, religions, cultural patterns that travelers will notice. Not a demographics lecture — focus on what a traveler will experience. How do people greet each other? What's considered polite or rude?

### Books (`books.md`)

Reading recommendations that span the continent or capture its spirit. Travel writing, literature, history. A few well-described picks are better than a long undescribed list. Each entry should say what the book is about and why a traveler would want to read it. Don't create a `books/` subdirectory with POI entries — just write the recommendations directly in the section file.

### When to Go (`when_to_go.md`)

Climate patterns across the continent. Best times for different regions. Monsoons, dry seasons, shoulder seasons. When are the crowds, when is it cheapest. This is especially useful for continents with dramatically different climate zones.

### Highlights (`highlights.md`)

The big reasons to visit this continent — the places, experiences, and landscapes that define it. This is the continent-level equivalent of the country highlights page. Mix different types: nature, history, food, adventure, culture, cities. A traveler reading this should come away with a shortlist of places they want to go.

Link generously to country and city pages. This section helps travelers who know they want to visit "somewhere in Africa" or "somewhere in Asia" narrow it down.

### Things to Do (`things_to_do.md`)

Big-picture activities that define travel on this continent. Safari in Africa, trekking in Asia, road-tripping in North America, island-hopping in the Pacific. Not an exhaustive list — a curated overview of the experiences that make this continent distinctive.

### Food (`food.md`)

A continent-level overview of the food landscape. What are the major culinary traditions? How does the food change as you move across regions? What should a traveler expect and seek out? This isn't about specific restaurants — it's about cuisines, ingredients, and food cultures at the macro level. Every continent has a food story worth telling.

## Sections to delete

These are legacy sections from the original World66 that don't belong at the continent level. Delete them when encountered:

- `tours_and_excursio.md` — spam or empty
- `travel_guide.md` — generic SEO content
- `beaches.md` — belongs on country/city pages
- `getting_there.md` — belongs on country pages (exception: Antarctica, where it makes sense)
- `budget_travel_idea.md`, `family_travel_idea.md`, `senior_travel_idea.md` — legacy empty sections
- `webcams.md` — obsolete
- Any city-level sections (eating_out, bars_and_cafes, nightlife, shopping, museums, day_trips)

## Cleanup rules

When reviewing continent pages, apply the same cleanup rules as for countries:

- **Fix markdown artifacts** — `**** **`, `&ldquo;`, `&rsquo;`, `&prime;`, `"/>` and other HTML entity junk
- **Replace CIA World Factbook data dumps** — especially in `people.md`
- **Replace dead Amazon links** — in `books.md`, rewrite as inline prose recommendations
- **Remove SEO-style openers** — no "**Africa travel** is a major..." keyword-stuffed intros
- **Fix outdated references** — defunct airlines, old currencies, 1990s prices
- **Remove spam** — tour operator ads, hotel listings, personal emails, gibberish files

## What we currently have vs. what we need

### Africa
Overview could use a refresh. Has: getting_around, health, books, practical_informat, when_to_go, things_to_do. Missing: people, highlights, food.

### Asia
Overview needs a refresh (typos, outdated "hippies" framing). Has: getting_around, health, practical_informat, when_to_go, things_to_do, food (legacy), books. Missing: people, highlights. Legacy language.md could be reviewed.

### Europe
Good overview. Has: getting_around, practical_informat, when_to_go, things_to_do, people, books. Health not needed. Missing: highlights, food.

### North America
Overview rewritten. Has: getting_around, health, practical_informat, books, people, when_to_go, things_to_do. Missing: highlights, food. Delete: tours_and_excursio.

### South America
Good overview with personality. Has: getting_around, health, practical_informat, books, when_to_go, things_to_do. Missing: people, highlights, food. Delete: tours_and_excursio.

### Australia and Pacific
Overview is brief. Has: getting_around, health, practical_informat, when_to_go, people, books, things_to_do. Missing: highlights, food. Delete: travel_guide.

### Antarctica
Appropriately short. Has: getting_there (makes sense here), getting_around, books, people, when_to_go, things_to_do. Missing: highlights. Food/health not applicable.

## Principles

- **Continent pages are for continent-level information.** Don't duplicate what belongs on country or city pages. If a section only applies to one country, it belongs on that country's page.
- **Link generously.** The continent overview is a navigation aid. Every country and major city mentioned should link to its page.
- **Update the overview when adding countries.** If you add a new country page, make sure it's mentioned and linked in the continent overview.
- **Keep section files at continent level to a sensible set.** Sections like "eating_out" or "nightlife" don't make sense for a whole continent — those belong on cities and countries.
- **Quality over completeness.** A well-written getting_there section is more valuable than five stub sections. Write the important ones well before filling in everything.
