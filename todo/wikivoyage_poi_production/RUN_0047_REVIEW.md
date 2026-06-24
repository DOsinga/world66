# Wikivoyage POI production run 0047

Processed batches: 0460-0469

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 23,450
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 15,815

All ten batches in this wave were all-reject batches. Every row had a candidate score below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0460 | 0 | 50 |
| 0461 | 0 | 50 |
| 0462 | 0 | 50 |
| 0463 | 0 | 50 |
| 0464 | 0 | 50 |
| 0465 | 0 | 50 |
| 0466 | 0 | 50 |
| 0467 | 0 | 50 |
| 0468 | 0 | 50 |
| 0469 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
