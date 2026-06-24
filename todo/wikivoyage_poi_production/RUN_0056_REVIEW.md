# Wikivoyage POI production run 0056

Processed batches: 0550-0559

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 27,950
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 20,315

All ten batches in this wave were all-reject batches. Every row had a candidate score of 0.51, below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0550 | 0 | 50 |
| 0551 | 0 | 50 |
| 0552 | 0 | 50 |
| 0553 | 0 | 50 |
| 0554 | 0 | 50 |
| 0555 | 0 | 50 |
| 0556 | 0 | 50 |
| 0557 | 0 | 50 |
| 0558 | 0 | 50 |
| 0559 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
