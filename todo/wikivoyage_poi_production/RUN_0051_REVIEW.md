# Wikivoyage POI production run 0051

Processed batches: 0500-0509

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 25,450
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 17,815

All ten batches in this wave were all-reject batches. Every row had a candidate score of 0.55, below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0500 | 0 | 50 |
| 0501 | 0 | 50 |
| 0502 | 0 | 50 |
| 0503 | 0 | 50 |
| 0504 | 0 | 50 |
| 0505 | 0 | 50 |
| 0506 | 0 | 50 |
| 0507 | 0 | 50 |
| 0508 | 0 | 50 |
| 0509 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
