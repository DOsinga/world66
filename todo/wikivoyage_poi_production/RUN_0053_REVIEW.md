# Wikivoyage POI production run 0053

Processed batches: 0520-0529

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 26,450
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 18,815

All ten batches in this wave were all-reject batches. Every row had a candidate score below the production threshold, so no POI markdown files were created.

Batches 0528-0529 dropped to a candidate score of 0.51; the earlier batches remained below threshold as well.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0520 | 0 | 50 |
| 0521 | 0 | 50 |
| 0522 | 0 | 50 |
| 0523 | 0 | 50 |
| 0524 | 0 | 50 |
| 0525 | 0 | 50 |
| 0526 | 0 | 50 |
| 0527 | 0 | 50 |
| 0528 | 0 | 50 |
| 0529 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
