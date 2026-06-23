# Wikivoyage POI Production Run 0014

Processed batches: `0130` through `0139`

Rows processed: 500

Accepted POIs: 220

Rejected rows: 280

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0130 | 34 | 16 |
| 0131 | 32 | 18 |
| 0132 | 14 | 36 |
| 0133 | 15 | 35 |
| 0134 | 18 | 32 |
| 0135 | 20 | 30 |
| 0136 | 18 | 32 |
| 0137 | 21 | 29 |
| 0138 | 22 | 28 |
| 0139 | 26 | 24 |

## Integration Notes

Workers accepted 220 POIs and rejected 280 rows. Central duplicate review found no same-parent duplicate POI titles and did not convert any accepted POIs into rejects.

Remaining global duplicate-title warnings were reviewed as distinct same-name places:

- `Church of St Nicholas`
- `Fort Louis`
- `Holy Mother of God Cathedral`
- `National Museum of Natural History`
- `Saint Mary's Cathedral`
- `Shevchenko Park`
- `St Joseph's Cathedral`
- `St Mary's Church`
- `St Michael's Church`
- `St Paul's Church`

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

Rows processed through batch `0139`: 6,950

Accepted POIs: 3,608

Rejected rows: 3,342
