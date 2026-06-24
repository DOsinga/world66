# Wikivoyage POI production run 0059

Processed batches: 0580-0589

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 29,450
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 21,815

All ten batches in this wave were all-reject batches. Every row had a candidate score below the production threshold, so no POI markdown files were created.

The wave continued the low-score tail, with candidates at 0.48 and then 0.47.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0580 | 0 | 50 |
| 0581 | 0 | 50 |
| 0582 | 0 | 50 |
| 0583 | 0 | 50 |
| 0584 | 0 | 50 |
| 0585 | 0 | 50 |
| 0586 | 0 | 50 |
| 0587 | 0 | 50 |
| 0588 | 0 | 50 |
| 0589 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
