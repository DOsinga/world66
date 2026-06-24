# Wikivoyage POI production run 0022

- Batches processed: `0210` through `0219`
- Rows processed: 500
- Accepted POIs: 293
- Rejected rows: 207
- Cumulative rows processed: 10,950
- Cumulative accepted POIs: 5,309
- Cumulative rejected rows: 5,641

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0210 | 24 | 26 |
| 0211 | 22 | 28 |
| 0212 | 32 | 18 |
| 0213 | 30 | 20 |
| 0214 | 24 | 26 |
| 0215 | 26 | 24 |
| 0216 | 40 | 10 |
| 0217 | 40 | 10 |
| 0218 | 28 | 22 |
| 0219 | 27 | 23 |

## Integration notes

Central duplicate review converted eight initially accepted POIs into rejects:

- `Memorial for peace` in `europe/france/normandybrittany/caen`, already covered by `memorial_de_caen.md`.
- `Cantor Center For The Arts` in `northamerica/unitedstates/california/palo_alto`, already covered by `cantor_arts_center.md`.
- `Old West Museum & Store` in `northamerica/unitedstates/wyoming/cheyenne`, already covered by `old_west_museum.md`.
- `Kansas City Zoo` in `northamerica/unitedstates/kansas/kansascity`, already covered by the existing Kansas City Zoo POI.
- `Long Beach Performing Arts Center` in `northamerica/unitedstates/california/long_beach`, already covered by the existing Long Beach Performing Arts Center POI.
- `Perot Theatre` in `northamerica/unitedstates/texas/texarkana`, already covered by the existing Perot Theatre POI.
- `Rabat Zoo` in `africa/morocco/rabat`, already covered by the existing Rabat Zoo POI.
- `The Money Museum` in `northamerica/unitedstates/kansas/kansascity`, already covered by `northamerica/unitedstates/missouri/kansascity/money_museum.md`.

Remaining global duplicate-title warnings were reviewed as distinct same-name places or generic names in different destinations:

- `Cathedrale Saint-Etienne`
- `Cathedral of the Most Holy Trinity`
- `Central Park`
- `Christuskirche`
- `Hofgarten`
- `Museum of Natural Science`
- `National Museum of History`
- `Nieuwe Kerk`
- `Pavilion Theatre`
- `Regent Theatre`
- `Sacred Heart Cathedral`
- `St Mark's Church`
- `St Paul's Church`
- `The Elms`
- `Uptown Theatre`
- `Waterfront Park`

## Validation

- Frontmatter/body validator: 293 new POIs, 0 errors.
- Broken local link check: 0 broken links.
- Django system check: passed.
