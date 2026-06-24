# Wikivoyage POI production run 0057

Processed batches: 0560-0569

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 28,450
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 20,815

All ten batches in this wave were all-reject batches. Every row had a candidate score of 0.51, below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0560 | 0 | 50 |
| 0561 | 0 | 50 |
| 0562 | 0 | 50 |
| 0563 | 0 | 50 |
| 0564 | 0 | 50 |
| 0565 | 0 | 50 |
| 0566 | 0 | 50 |
| 0567 | 0 | 50 |
| 0568 | 0 | 50 |
| 0569 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
