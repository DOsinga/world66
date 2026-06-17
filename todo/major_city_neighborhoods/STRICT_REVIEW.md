# Strict review of open neighbourhood PRs — for review

Applies the same strict lens we used on Bangkok / Florence / Dublin to the other open
`major_city_neighborhoods` PRs. Scope = the cities each PR actually added neighbourhoods to.

## Headline

**The neighbourhoods in these PRs are mostly fine** — they're real, recognisable visitor
districts. The "suspicious" name flags (Gothic Quarter, Latin Quarter, The Strip, The Loop,
Coptic Quarter) are all legitimate. Unlike Bangkok/Florence/Dublin, these don't need
structural neighbourhood surgery.

**The real, repo-wide issue is duplicate POIs** — the neighbourhood work created a second
copy of many places (usually named `<neighbourhood>_<place>`) alongside a pre-existing flat
POI. There are ~28 duplicate pairs across these cities.

⚠️ **Do not bulk-delete by matching title** — several "duplicates" are actually *mis-titled*
distinct places. Confirmed traps:
- Chicago `lincoln_park_second_city.md` is titled **"Chicago History Museum"** but is almost
  certainly The Second City comedy club — a mis-title, not a dup.
- Marrakesh `yves_st_laurent_g.md` is titled **"Majorelle Garden"** but is the adjacent **YSL
  Museum** (a separate attraction).
- Chicago `hyde_park_medici_coffeehouse` ("Medici on 57th") vs `medici_restaurant` — verify
  these aren't two different Medici venues.

Each pair below lists `keep` / `delete` by score, but **verify the title actually matches the
content before deleting.**

## Duplicate POI pairs (keep higher score; union the neighbourhood tag onto the survivor)

### PR #2060 (batch_0001)
- **Shanghai** — jin mao tower (`jin_mao_tower` 8.5 / `pudong_jin_mao` 8.5); oriental pearl
  (`pudong_oriental_pearl` 8.5 > `oriental_pearl` 7.1); power station of art
  (`power_station_of_art` 7.5 / `pudong_power_station_art` 7.5)
- **Delhi** — khan market (`defence_colony_khan_market` 8.0 > `khan_market` 6.5); gandhi smriti
  (`gandhi_smriti` 8.5 > `gandhimuseum` 7.8)
- **Mumbai** — hanging gardens (`malabar_nana_nani_park` 7.5 > `hanginggardens` 5.8)
- **Madrid** — café comercial, la casa encendida, el tigre, mercado de san antón,
  plaza de lavapiés, plaza del dos de mayo (6 pairs; the `<nbhd>_…` copy duplicates a flat one)
- **Chicago** — museum of science and industry (`hyde_park_museum_science_industry` /
  `museum_of_science` 8.5), national museum of mexican art (`mexican_fine_arts` 8.2 /
  `pilsen_national_museum_mexican_art` 8.0), river north gallery district (+_ext).
  ⚠️ "chicago history museum" and "medici on 57th" pairs look mis-titled — verify, don't delete blind.

### PR #2070 (batch_0003b)
- **Cape Town** — table mountain (`tablemountain` 9.8 / `tablemountain_td` 9.8)
- **Barcelona** — none (neighbourhoods clean)

### PR #2073 (batch_0004a)
- **Marrakesh** — ⚠️ majorelle garden: `majorelle_garden` (9.1) is the garden; `yves_st_laurent_g`
  (9.0, titled "Majorelle Garden") is really the **YSL Museum** → **re-title, don't delete**.
- **Havana** — marina hemingway (`playa_marina` 7.4 / `marina_hemingway` 7.1)

### PR #2074 (batch_0004b)
- **Cairo** — tahrir square (`tahrir_square` 8.5 / `garden_city_tahrir` 8.5)
- **Kuala Lumpur** — thean hou temple (`theanhoutemple` 8.1 / `thean_hou_temple` 8.0)

### PR #2077 (batch_0005)
- **Kyoto** — philosopher's path: `philosophers_path` (7.7, canonical POI) vs `philosophers_walk`
  (8.5, the page I down-graded from a neighbourhood). Same path → keep one, retag.
- **Edinburgh** — greyfriars kirkyard (`greyfriars` 8.8 / `greyfriars_kirkyard` 7.5);
  victoria street (`victoria_street` 8.6 / `victoria_street_shops` 7.5)

## POI == neighbourhood name clashes (the "Chinatown" pattern — POI duplicates its own district)

- **KL** — `lakegardens.md` POI ("Lake Gardens") duplicates the **Lake Gardens** neighbourhood → delete the POI.
- **Edinburgh** — `things_to_do_stockbridge.md` POI ("Stockbridge") duplicates the **Stockbridge** neighbourhood → delete the POI.
- **NYC** — `staten_island.md` POI duplicates the **Staten Island** "neighbourhood" (which also
  has a bogus `score: 0.37` — neighbourhoods take no score). Delete the POI; fix the score.
- **Marrakesh** — `bab_doukkala.md` is the **city gate** (a real POI), clashing with the
  Bab Doukkala district → **re-title the POI "Bab Doukkala Gate"** (not a dup).

## Out-of-town POIs to confirm are in `day_trips`, not `things_to_do`

Most far-flung entries are genuine day trips and likely already tagged correctly, but worth a
spot-check that none sit in the in-city list:
- **Vegas** — Grand Canyon West, Death Valley, Hoover Dam, Red Rock, Valley of Fire, Area 51, Mt Charleston (all day trips)
- **NYC** — Atlantic City, Cape May, Rockaway Beach, Bronx Botanical Garden, the Staten Island museums
- **Krakow** — Auschwitz-Birkenau, Zakopane
- **Cape Town** — Cape Point, Boulders Beach, Simon's Town, the Winelands
- **Mumbai** — Sanjay Gandhi NP, Kanheri Caves, Kalamb Beach
- plus assorted in Shanghai (Disneyland), Marrakesh (ANIMA), Copenhagen (Louisiana, ARKEN), Taipei (Jiufen)

## Neighbourhood verdict per city (all judged OK unless noted)

All neighbourhood sets reviewed are coherent visitor districts. None need merging/cutting like
Bangkok/Florence/Dublin did. Minor notes:
- **NYC** mixes boroughs (Brooklyn, Queens, Staten Island) with neighbourhoods (SoHo, West
  Village…) — defensible but inconsistent granularity; worth a future tidy.
- **Vegas** has only 4 (Strip, Downtown, Arts District, Chinatown) — fine for Vegas.

## Recommendation

The dedup is mechanical but trap-laden (mis-titles). Suggest doing it **city-by-city with a
quick eyeball** rather than a blind script. Happy to execute on your go-ahead, PR by PR.
