# Wikivoyage POI Production Run 0005

Processed batches: `0040` through `0049`

## Result

- Rows processed: 500
- Accepted POIs: 414
- Rejected rows: 86
- Section files added: 1

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0040 | 44 | 6 |
| 0041 | 44 | 6 |
| 0042 | 45 | 5 |
| 0043 | 45 | 5 |
| 0044 | 40 | 10 |
| 0045 | 37 | 13 |
| 0046 | 38 | 12 |
| 0047 | 42 | 8 |
| 0048 | 41 | 9 |
| 0049 | 38 | 12 |

## Validation

- Frontmatter parse and required POI fields: passed
- Coordinate bounds and `score >= 6`: passed
- First tag `things_to_do`: passed
- Sources present and at least two body paragraphs: passed
- Duplicate title under same parent: none found
- Broken local markdown links in new files: none found
- Django system check: passed

## Notes

One missing `things_to_do.md` section page was added for `content/northamerica/unitedstates/california/sanjose/` so the new San Jose Museum of Art POI has the expected section filter available.

Cumulative production total after this run: 2,450 rows processed, 1,765 accepted POIs, 685 rejected rows.
