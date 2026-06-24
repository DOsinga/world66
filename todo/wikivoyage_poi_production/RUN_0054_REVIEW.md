# Wikivoyage POI production run 0054

Processed batches: 0530-0539

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 26,950
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 19,315

All ten batches in this wave were all-reject batches. Every row had a candidate score of 0.51, below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0530 | 0 | 50 |
| 0531 | 0 | 50 |
| 0532 | 0 | 50 |
| 0533 | 0 | 50 |
| 0534 | 0 | 50 |
| 0535 | 0 | 50 |
| 0536 | 0 | 50 |
| 0537 | 0 | 50 |
| 0538 | 0 | 50 |
| 0539 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
