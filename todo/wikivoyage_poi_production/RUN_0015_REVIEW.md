# Wikivoyage POI Production Run 0015

Processed batches: `0140` through `0149`

Rows processed: 500

Accepted POIs: 262

Rejected rows: 238

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0140 | 31 | 19 |
| 0141 | 30 | 20 |
| 0142 | 33 | 17 |
| 0143 | 32 | 18 |
| 0144 | 31 | 19 |
| 0145 | 26 | 24 |
| 0146 | 19 | 31 |
| 0147 | 25 | 25 |
| 0148 | 16 | 34 |
| 0149 | 19 | 31 |

## Integration Notes

Workers initially accepted 271 POIs and rejected 229 rows. Central duplicate review converted nine accepted POIs into rejects:

- `Ardenica Monastery -` under `europe/albania/lushnje`, duplicate of existing `europe/albania/ardenica/ardenica_monastery`
- `Eilat City Museum` under `asia/israel/eliat`, duplicate of existing `asia/israel/eilat/eilat_city_museum`
- `Guadalcanal American Memorial` under `australiaandpacific/solomonislands/guadalcanal`, duplicate of existing `australiaandpacific/solomonislands/honiara/guadalcanal_american_memorial`
- `Himmelbjerget` under `europe/denmark/silkeborg`, duplicate of existing `europe/denmark/ry/himmelbjerget`
- `Kemper Museum of Contemporary Art` under `northamerica/unitedstates/kansas/kansascity`, duplicate of existing `northamerica/unitedstates/missouri/kansascity/kemper_museum`
- `Minute Man National Historical Park` under `northamerica/unitedstates/massachusetts/concord`, duplicate of existing `northamerica/unitedstates/massachusetts/lexington/minute_man_national_historical_park`
- `Monte de San Pedro` under `europe/spain/northernspain/lacorua`, duplicate of existing `europe/spain/galicia/lacoruna/monte_de_san_pedro`
- `Phaung Daw Oo Pagoda` under `asia/myanmar/inlelake`, duplicate of existing `asia/myanmar/nyangshwe/phaung_daw_oo_pagoda`
- `Triveni Ghat` under `asia/india/uttarpradesh/rishikesh`, duplicate of existing `asia/india/uttaranchal/rishikesh/triveni_ghat`

Remaining global duplicate-title warnings were reviewed as distinct same-name places:

- `Centennial Park`
- `Commonwealth War Cemetery`
- `Corso Italia`
- `Jewish Cemetery`
- `Museum of Arts and Sciences`
- `Natural History Museum`
- `Regional Museum`
- `Tudor House Museum`
- `Zoological Museum`

Reject logs were normalized to the full candidate schema with `reject_reason`.

## Validation

- New POI frontmatter parses with `python-frontmatter`
- Required fields present: `title`, `type`, `latitude`, `longitude`, `tags`, `snippet`, `score`, `sources`
- `type: poi`, first tag `things_to_do`, valid coordinates, scores at least 6
- Bodies have at least two paragraphs
- No broken local markdown links in new files
- No same-parent duplicate POI titles
- Django system check passed

## Cumulative Production Totals

Rows processed through batch `0149`: 7,450

Accepted POIs: 3,870

Rejected rows: 3,580
