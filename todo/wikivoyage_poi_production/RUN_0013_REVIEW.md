# Wikivoyage POI Production Run 0013

Processed batches: `0120` through `0129`

Rows processed: 500

Accepted POIs: 178

Rejected rows: 322

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0120 | 12 | 38 |
| 0121 | 17 | 33 |
| 0122 | 18 | 32 |
| 0123 | 10 | 40 |
| 0124 | 30 | 20 |
| 0125 | 22 | 28 |
| 0126 | 21 | 29 |
| 0127 | 22 | 28 |
| 0128 | 13 | 37 |
| 0129 | 13 | 37 |

## Integration Notes

Workers initially accepted 184 POIs and rejected 316 rows. Central duplicate review converted six accepted POIs into rejects:

- `Alice Keck Park Memorial Garden` under `northamerica/unitedstates/california/santa_barbara`, duplicate of existing `northamerica/unitedstates/california/centralcoast/santabarbara/alice_keck_park_garden`
- `Arroyo Burro Beach` under `northamerica/unitedstates/california/santa_barbara`, duplicate of existing `northamerica/unitedstates/california/centralcoast/santabarbara/arroyo_burro_beach`
- `El Caracol` under `northamerica/mexico/chichenitza`, duplicate of existing `northamerica/mexico/yucatan/chichen_itza/el_caracol`
- `Ishiteji` under `asia/japan/shikoku/matsuyama`, duplicate of existing `asia/japan/shikoku/ehime/ishite_ji`
- `Moraine Lake` under `northamerica/canada/alberta/lake_louise`, duplicate of existing `northamerica/canada/alberta/banff/moraine_lake`
- `Noordertoren` under `europe/netherlands/waddenislands/schiermonnikoog_is/schiermonnikoog`, duplicate of existing `europe/netherlands/waddenislands/schiermonnikoog_is/noordertoren`

Remaining global duplicate-title warnings were reviewed as distinct same-name places:

- `Centro Civico`
- `Dominican Monastery`
- `Old Jewish Cemetery`
- `Railway Museum`
- `Tianning Temple`

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

Rows processed through batch `0129`: 6,450

Accepted POIs: 3,388

Rejected rows: 3,062
