# Wikivoyage POI production run 0045

Processed batches: 0440-0449

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 22,450
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 14,815

All ten batches in this wave were all-reject batches. Every row had a candidate score below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0440 | 0 | 50 |
| 0441 | 0 | 50 |
| 0442 | 0 | 50 |
| 0443 | 0 | 50 |
| 0444 | 0 | 50 |
| 0445 | 0 | 50 |
| 0446 | 0 | 50 |
| 0447 | 0 | 50 |
| 0448 | 0 | 50 |
| 0449 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
