# Wikivoyage POI Production Run 0008

Processed batches: `0070` through `0079`

## Result

- Rows processed: 500
- Accepted POIs: 229
- Rejected rows: 271
- Section files added: 0

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0070 | 23 | 27 |
| 0071 | 23 | 27 |
| 0072 | 25 | 25 |
| 0073 | 23 | 27 |
| 0074 | 25 | 25 |
| 0075 | 28 | 22 |
| 0076 | 18 | 32 |
| 0077 | 20 | 30 |
| 0078 | 23 | 27 |
| 0079 | 21 | 29 |

## Validation

- Frontmatter parse and required POI fields: passed
- Coordinate bounds and `score >= 6`: passed
- First tag `things_to_do`: passed
- Sources present and at least two body paragraphs: passed
- Duplicate title under same parent: none found
- Broken local markdown links in new files: none found
- Django system check: passed

## Notes

Three initially accepted rows were converted to rejections after the global duplicate-title pass:

- New Camaldoli Hermitage
- Como-Brunate Funicular
- Winchester Mystery House

Reject logs for batches `0074` through `0077` were normalized back to the full production schema after workers wrote abbreviated reject CSVs.

The remaining global title matches are different places with shared names: Casa de la Cultura and Riverside Nature Center.

Cumulative production total after this run: 3,950 rows processed, 2,459 accepted POIs, 1,491 rejected rows.
