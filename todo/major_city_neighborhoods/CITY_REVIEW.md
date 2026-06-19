# City review — open neighbourhood PRs

For each city: the final neighbourhood set (with how many POIs each collects) after the strict pass + dedup.

### How to view a city live
The site reads content from disk, so to browse a branch's version of a city, overlay it into your working tree (server auto-reloads), then open the URL. Revert with the same path off `HEAD`.
```bash
# view  →  git checkout origin/<branch> -- content/<city-path>
# undo  →  git checkout HEAD -- content/<city-path>
```
The running server is at http://localhost:8066

## ⚠️ Flags — neighbourhoods with 0–1 POIs (candidates to fill or drop)

- singapore: **Orchard Road** (1)
- singapore: **Sentosa** (1)
- singapore: **Tanjong Pagar** (0)
- singapore: **Tiong Bahru** (0)
- hochiminhcity: **District 7 (Phu My Hung)** (0)
- hochiminhcity: **Thao Dien** (0)

---

## PR #2060 — `batch_0001`  ([open](https://github.com/DOsinga/world66/pull/2060))

### Shanghai — 5 neighbourhoods, 119 POIs
`http://localhost:8066/asia/china/shanghai`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0001 -- content/asia/china/shanghai`

- **Neighbourhoods:** City Center (Renmin Square) (13), Hongkou (13), Jing'an (10), Lujiazui (15), Tianzifang (10)
- **Sections:** bars_and_cafes=6, shopping=14, things_to_do=112

### Delhi — 7 neighbourhoods, 86 POIs
`http://localhost:8066/asia/india/delhi`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0001 -- content/asia/india/delhi`

- **Neighbourhoods:** Defence Colony (8), Karol Bagh (10), Lodhi Colony (7), Lutyens' Delhi (8), Mehrauli (8), Nizamuddin (9), Old Delhi (10)
- **Sections:** bars_and_cafes=6, shopping=23, things_to_do=80

### Mumbai — 7 neighbourhoods, 77 POIs
`http://localhost:8066/asia/india/maharashtra/mumbai`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0001 -- content/asia/india/maharashtra/mumbai`

- **Neighbourhoods:** Andheri (8), Bandra-Kurla Complex (6), Fort (7), Juhu (5), Lower Parel (8), Malabar Hill (8), Worli (8)
- **Sections:** bars_and_cafes=5, shopping=11, things_to_do=74

### Madrid — 10 neighbourhoods, 72 POIs
`http://localhost:8066/europe/spain/madrid`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0001 -- content/europe/spain/madrid`

- **Neighbourhoods:** Argüelles (9), Chamberí (6), Chueca (12), Huertas (8), La Latina (5), Lavapiés (11), Malasaña (10), Retiro (7), Salamanca (11), Sol and Centro (2)
- **Sections:** bars_and_cafes=11, eating_out=9, shopping=10, things_to_do=61

### Chicago — 8 neighbourhoods, 139 POIs
`http://localhost:8066/northamerica/unitedstates/illinois/chicago`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0001 -- content/northamerica/unitedstates/illinois/chicago`

- **Neighbourhoods:** Hyde Park (13), Lakeview and Wrigleyville (14), Lincoln Park (13), Old Town (12), River North (13), South Loop (15), The Loop (14), Ukrainian Village (14)
- **Sections:** bars_and_cafes=17, eating_out=10, shopping=14, things_to_do=120


## PR #2065 — `batch_0002a`  ([open](https://github.com/DOsinga/world66/pull/2065))

### Singapore — 11 neighbourhoods, 44 POIs
`http://localhost:8066/asia/singapore`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0002a -- content/asia/singapore`

- **Neighbourhoods:** Bugis (4), Chinatown (5), Clarke Quay & the River (6), Kampong Glam (3), Katong & Joo Chiat (3), Little India (3), Marina Bay (6), Orchard Road (1), Sentosa (1), Tanjong Pagar (0), Tiong Bahru (0)
- **Sections:** bars_and_cafes=5, beaches=1, eating_out=2, shopping=4, things_to_do=33

### Hochiminhcity — 8 neighbourhoods, 55 POIs
`http://localhost:8066/asia/vietnam/hochiminhcity`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0002a -- content/asia/vietnam/hochiminhcity`

- **Neighbourhoods:** Ben Thanh (9), Cholon (Chinatown) (2), Da Kao (3), District 1 (French Quarter) (21), District 3 (5), District 7 (Phu My Hung) (0), Pham Ngu Lao (9), Thao Dien (0)
- **Sections:** bars_and_cafes=12, eating_out=12, shopping=5, things_to_do=25

### Milan — 10 neighbourhoods, 37 POIs
`http://localhost:8066/europe/italy/lombardia/milan`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0002a -- content/europe/italy/lombardia/milan`

- **Neighbourhoods:** Brera (2), Castello e Sempione (4), Centro Storico (9), Isola (3), Navigli (2), Porta Nuova (4), Porta Romana (2), Porta Venezia (3), Quadrilatero della Moda (4), Tortona (3)
- **Sections:** bars_and_cafes=4, eating_out=3, shopping=1, things_to_do=29


## PR #2067 — `batch_0002b`  ([open](https://github.com/DOsinga/world66/pull/2067))

### Taipei — 10 neighbourhoods, 90 POIs
`http://localhost:8066/asia/taiwan/taipei`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0002b -- content/asia/taiwan/taipei`

- **Neighbourhoods:** Beitou (7), Da'an District (12), Datong District (10), Shilin District (10), Songshan (8), Wanhua District (8), Ximending (6), Xinyi District (7), Zhongshan District (8), Zhongzheng (10)
- **Sections:** bars_and_cafes=3, eating_out=9, shopping=7, things_to_do=79

### Krakow — 10 neighbourhoods, 81 POIs
`http://localhost:8066/europe/poland/krakow`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0002b -- content/europe/poland/krakow`

- **Neighbourhoods:** Grzegórzki (5), Kazimierz (13), Kleparz (8), Nowa Huta (7), Old Town (Stare Miasto) (25), Piasek (8), Podgórze (6), Salwator i Zwierzyniec (4), Stradom (4), Wawel (6)
- **Sections:** bars_and_cafes=5, eating_out=5, shopping=3, things_to_do=70


## PR #2071 — `batch_0003a`  ([open](https://github.com/DOsinga/world66/pull/2071))

### Bangkok — 10 neighbourhoods, 98 POIs
`http://localhost:8066/asia/thailand/bangkok`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0003a -- content/asia/thailand/bangkok`

- **Neighbourhoods:** Ari (8), Banglamphu (9), Chinatown (9), Dusit (9), Pratunam (5), Rattanakosin (10), Siam (15), Silom (9), Sukhumvit (7), Thonburi (9)
- **Sections:** bars_and_cafes=10, day_trips=4, eating_out=12, shopping=20, things_to_do=31

### Dublin — 6 neighbourhoods, 124 POIs
`http://localhost:8066/europe/ireland/dublin`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0003a -- content/europe/ireland/dublin`

- **Neighbourhoods:** Docklands (10), Georgian Quarter (12), Kilmainham (10), O'Connell Street (11), Temple Bar (11), The Liberties (12)
- **Sections:** bars_and_cafes=9, beaches=3, day_trips=6, eating_out=13, shopping=7, things_to_do=53

### Florence — 6 neighbourhoods, 83 POIs
`http://localhost:8066/europe/italy/tuscany/florence`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0003a -- content/europe/italy/tuscany/florence`

- **Neighbourhoods:** Centro Storico (19), Oltrarno (17), San Lorenzo (9), San Marco (9), Santa Croce (20), Santa Maria Novella (9)
- **Sections:** bars_and_cafes=6, eating_out=12, shopping=6, things_to_do=33


## PR #2070 — `batch_0003b`  ([open](https://github.com/DOsinga/world66/pull/2070))

### Capetown — 11 neighbourhoods, 75 POIs
`http://localhost:8066/africa/southafrica/capetown`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0003b -- content/africa/southafrica/capetown`

- **Neighbourhoods:** Atlantic Seaboard (3), Bo-Kaap (5), City Bowl (29), De Waterkant (3), Green Point (6), Observatory (4), Sea Point (3), Southern Peninsula (7), Southern Suburbs (5), Victoria & Alfred Waterfront (4), Woodstock (3)
- **Sections:** bars_and_cafes=6, day_trips=5, eating_out=10, shopping=2, things_to_do=61

### Barcelona — 10 neighbourhoods, 83 POIs
`http://localhost:8066/europe/spain/catalonia/barcelona`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0003b -- content/europe/spain/catalonia/barcelona`

- **Neighbourhoods:** Barceloneta (8), Eixample (15), El Born (7), El Raval (8), Gothic Quarter (11), Gràcia (7), Les Corts (6), Montjuïc (7), Poble-sec (5), Sant Martí (5)
- **Sections:** bars_and_cafes=17, beaches=1, eating_out=13, shopping=13, things_to_do=38


## PR #2073 — `batch_0004a`  ([open](https://github.com/DOsinga/world66/pull/2073))

### Marrakesh — 10 neighbourhoods, 82 POIs
`http://localhost:8066/africa/morocco/marrakesh`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0004a -- content/africa/morocco/marrakesh`

- **Neighbourhoods:** Agdal (8), Bab Doukkala (6), Guéliz (3), Hivernage (4), Kasbah (7), Medina (11), Mellah (4), Palmeraie (4), Semlalia (7), Sidi Ghanem (4)
- **Sections:** eating_out=2, shopping=9, things_to_do=46

### Copenhagen — 9 neighbourhoods, 92 POIs
`http://localhost:8066/europe/denmark/copenhagen`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0004a -- content/europe/denmark/copenhagen`

- **Neighbourhoods:** Christiania (9), Christianshavn (9), Copenhagen Harbourfront (10), Latin Quarter (11), Meatpacking District (8), Nørrebro (7), Stroget (11), Vesterbro (9), Østerbro (10)
- **Sections:** bars_and_cafes=13, eating_out=10, shopping=2, things_to_do=61

### Havana — 10 neighbourhoods, 85 POIs
`http://localhost:8066/northamerica/thecaribbean/cuba/havana`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0004a -- content/northamerica/thecaribbean/cuba/havana`

- **Neighbourhoods:** Centro Habana (6), El Cerro (7), Habana del Este (9), La Habana Vieja (Old Havana) (5), Miramar (8), Nuevo Vedado (8), Playa (7), Regla (7), San Miguel del Padrón (8), Vedado (5)
- **Sections:** bars_and_cafes=6, eating_out=5, shopping=1, things_to_do=59


## PR #2074 — `batch_0004b`  ([open](https://github.com/DOsinga/world66/pull/2074))

### Cairo — 9 neighbourhoods, 75 POIs
`http://localhost:8066/africa/egypt/cairo`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0004b -- content/africa/egypt/cairo`

- **Neighbourhoods:** Coptic Quarter (8), Dokki (7), Downtown Cairo (10), Garden City (4), Heliopolis (7), Islamic Cairo (13), Maadi (5), Mohandiseen (4), Zamalek (10)
- **Sections:** bars_and_cafes=7, eating_out=12, shopping=4, things_to_do=48

### Kualalumpur — 9 neighbourhoods, 94 POIs
`http://localhost:8066/asia/malaysia/kualalumpur`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0004b -- content/asia/malaysia/kualalumpur`

- **Neighbourhoods:** Bangsar (9), Brickfields (9), Bukit Bintang (8), Chinatown (13), KLCC (9), Kampung Baru (8), Lake Gardens (10), Masjid India (10), Mont Kiara (8)
- **Sections:** bars_and_cafes=6, eating_out=21, shopping=15, things_to_do=47


## PR #2077 — `batch_0005`  ([open](https://github.com/DOsinga/world66/pull/2077))

### Kyoto — 7 neighbourhoods, 98 POIs
`http://localhost:8066/asia/japan/honshu/kyoto`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0005 -- content/asia/japan/honshu/kyoto`

- **Neighbourhoods:** Arashiyama (12), Downtown Kyoto (12), Fushimi (10), Gion (15), Higashiyama (13), Nijo (11), Nishiki and Kawaramachi (12)
- **Sections:** bars_and_cafes=10, eating_out=30, shopping=2, things_to_do=98

### Rome — 10 neighbourhoods, 124 POIs
`http://localhost:8066/europe/italy/lazio/rome`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0005 -- content/europe/italy/lazio/rome`

- **Neighbourhoods:** Aventino (10), Campo de' Fiori (15), Esquilino (10), Monti (11), Pantheon & Navona (15), Parioli (10), Pigneto (10), Prati (12), Testaccio (16), Trastevere (13)
- **Sections:** bars_and_cafes=12, eating_out=28, shopping=10, things_to_do=72

### Newyork — 12 neighbourhoods, 123 POIs
`http://localhost:8066/northamerica/unitedstates/newyorkstate/newyork`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0005 -- content/northamerica/unitedstates/newyorkstate/newyork`

- **Neighbourhoods:** Brooklyn (10), Brooklyn Heights (9), Harlem (10), Long Island City (10), Lower East Side (10), Midtown (13), Queens (9), SoHo (13), Staten Island (10), Upper West Side (9), West Village (10), Williamsburg (10)
- **Sections:** bars_and_cafes=12, day_trips=4, eating_out=23, shopping=8, things_to_do=81

### Edinburgh — 8 neighbourhoods, 87 POIs
`http://localhost:8066/europe/unitedkingdom/scotland/edinburgh`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0005 -- content/europe/unitedkingdom/scotland/edinburgh`

- **Neighbourhoods:** Canongate (10), Grassmarket & Cowgate (8), Leith (9), Morningside (10), New Town (10), Old Town (23), Portobello (7), Stockbridge (8)
- **Sections:** bars_and_cafes=29, eating_out=11, shopping=4, things_to_do=45

### Lasvegas — 4 neighbourhoods, 97 POIs
`http://localhost:8066/northamerica/unitedstates/nevada/lasvegas`  ·  overlay: `git checkout origin/todo-major_city_neighborhoods-batch_0005 -- content/northamerica/unitedstates/nevada/lasvegas`

- **Neighbourhoods:** Arts District (18b) (10), Chinatown (12), Downtown (12), The Strip (48)
- **Sections:** bars_and_cafes=15, day_trips=9, eating_out=17, shopping=10, things_to_do=44

