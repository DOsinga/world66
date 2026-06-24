# Wikivoyage POI production run 0049

Processed batches: 0480-0489

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 24,450
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 16,815

All ten batches in this wave were all-reject batches. Every row had a candidate score of 0.55, below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0480 | 0 | 50 |
| 0481 | 0 | 50 |
| 0482 | 0 | 50 |
| 0483 | 0 | 50 |
| 0484 | 0 | 50 |
| 0485 | 0 | 50 |
| 0486 | 0 | 50 |
| 0487 | 0 | 50 |
| 0488 | 0 | 50 |
| 0489 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
