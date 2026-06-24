# Wikivoyage POI production run 0048

Processed batches: 0470-0479

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 23,950
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 16,315

All ten batches in this wave were all-reject batches. Every row had a candidate score below the production threshold, so no POI markdown files were created.

Batches 0476-0479 dropped to a candidate score of 0.55; the rest of the wave remained below threshold as well.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0470 | 0 | 50 |
| 0471 | 0 | 50 |
| 0472 | 0 | 50 |
| 0473 | 0 | 50 |
| 0474 | 0 | 50 |
| 0475 | 0 | 50 |
| 0476 | 0 | 50 |
| 0477 | 0 | 50 |
| 0478 | 0 | 50 |
| 0479 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
