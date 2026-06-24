# Wikivoyage POI production run 0055

Processed batches: 0540-0549

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 27,450
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 19,815

All ten batches in this wave were all-reject batches. Every row had a candidate score of 0.51, below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0540 | 0 | 50 |
| 0541 | 0 | 50 |
| 0542 | 0 | 50 |
| 0543 | 0 | 50 |
| 0544 | 0 | 50 |
| 0545 | 0 | 50 |
| 0546 | 0 | 50 |
| 0547 | 0 | 50 |
| 0548 | 0 | 50 |
| 0549 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
