# Wikivoyage POI Production Run 0006

Processed batches: `0050` through `0059`

## Result

- Rows processed: 500
- Accepted POIs: 259
- Rejected rows: 241
- Section files added: 3

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0050 | 40 | 10 |
| 0051 | 39 | 11 |
| 0052 | 17 | 33 |
| 0053 | 13 | 37 |
| 0054 | 39 | 11 |
| 0055 | 33 | 17 |
| 0056 | 25 | 25 |
| 0057 | 26 | 24 |
| 0058 | 11 | 39 |
| 0059 | 16 | 34 |

## Validation

- Frontmatter parse and required POI fields: passed
- Coordinate bounds and `score >= 6`: passed
- First tag `things_to_do`: passed
- Sources present and at least two body paragraphs: passed
- Duplicate title under same parent: none found
- Broken local markdown links in new files: none found
- Django system check: passed

## Notes

Three missing `things_to_do.md` section pages were added for:

- `content/northamerica/unitedstates/california/centralcoast/monterey/bigsur/`
- `content/europe/unitedkingdom/england/norfolk/the_norfolk_broads/`
- `content/europe/unitedkingdom/scotland/forres/`

One Wikivoyage lead for Leigh Woods in `batch_0059` duplicated an existing World66 POI from an earlier production batch, so it was recorded as a rejection and the existing POI was left unchanged.

Cumulative production total after this run: 2,950 rows processed, 2,024 accepted POIs, 926 rejected rows.
