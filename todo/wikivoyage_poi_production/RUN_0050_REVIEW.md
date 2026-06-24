# Wikivoyage POI production run 0050

Processed batches: 0490-0499

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 24,950
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 17,315

All ten batches in this wave were all-reject batches. Every row had a candidate score of 0.55, below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0490 | 0 | 50 |
| 0491 | 0 | 50 |
| 0492 | 0 | 50 |
| 0493 | 0 | 50 |
| 0494 | 0 | 50 |
| 0495 | 0 | 50 |
| 0496 | 0 | 50 |
| 0497 | 0 | 50 |
| 0498 | 0 | 50 |
| 0499 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
