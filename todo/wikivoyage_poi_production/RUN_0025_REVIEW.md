# Wikivoyage POI production run 0025

- Batches processed: `0240` through `0249`
- Rows processed: 500
- Accepted POIs: 159
- Rejected rows: 341
- Cumulative rows processed: 12,450
- Cumulative accepted POIs: 5,912
- Cumulative rejected rows: 6,538

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0240 | 23 | 27 |
| 0241 | 29 | 21 |
| 0242 | 16 | 34 |
| 0243 | 18 | 32 |
| 0244 | 10 | 40 |
| 0245 | 10 | 40 |
| 0246 | 19 | 31 |
| 0247 | 16 | 34 |
| 0248 | 8 | 42 |
| 0249 | 10 | 40 |

## Integration notes

Central duplicate review converted three initially accepted POIs into rejects:

- `Bachkovo Monastery` in `europe/bulgaria/plovdiv`, already covered under the Rhodope Mountains/Smolyan path.
- `Smailholm Tower` in `europe/unitedkingdom/scotland/melrose`, already covered under Kelso.
- `Garganta del Diablo` in `southamerica/brazil/iguacufalls`, already covered under Puerto Iguazu.

Remaining global duplicate-title warnings were reviewed as distinct same-name places or generic names in different destinations:

- `Camera Obscura`
- `Charco Azul`
- `Iron Bridge`
- `Jewish Cemetery`
- `Meia Praia`
- `Peace Pagoda`
- `Regional Science Centre`
- `San Silvestro`
- `Stone Bridge`

## Validation

- Frontmatter/body validator: 159 new POIs, 0 errors.
- Broken local link check: 0 broken links.
- Same-parent duplicate check: 0 duplicate groups.
- Django system check: passed.
