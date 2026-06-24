# Wikivoyage POI production run 0027

- Batches processed: `0260` through `0269`
- Rows processed: 500
- Accepted POIs: 138
- Rejected rows: 362
- Cumulative rows processed: 13,450
- Cumulative accepted POIs: 6,168
- Cumulative rejected rows: 7,282

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0260 | 9 | 41 |
| 0261 | 10 | 40 |
| 0262 | 18 | 32 |
| 0263 | 16 | 34 |
| 0264 | 19 | 31 |
| 0265 | 15 | 35 |
| 0266 | 14 | 36 |
| 0267 | 16 | 34 |
| 0268 | 7 | 43 |
| 0269 | 14 | 36 |

## Integration notes

No initially accepted POIs required central duplicate conversion in this run.

Remaining global duplicate-title warnings were reviewed as distinct same-name places or generic names in different destinations:

- `Botanic Gardens`
- `New Town Hall`
- `Old Cemetery`
- `Palazzo della Ragione`

## Validation

- Frontmatter/body validator: 138 new POIs, 0 errors.
- Broken local link check: 0 broken links.
- Same-parent duplicate check: 0 duplicate groups.
- Django system check: passed.
