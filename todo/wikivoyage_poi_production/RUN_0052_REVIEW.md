# Wikivoyage POI production run 0052

Processed batches: 0510-0519

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 25,950
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 18,315

All ten batches in this wave were all-reject batches. Every row had a candidate score of 0.55, below the production threshold, so no POI markdown files were created.

Two initial workers disconnected before producing files for batches 0510-0511 and 0516-0517. Replacement workers processed those exact batches cleanly, and the central validation covered the replacement outputs.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0510 | 0 | 50 |
| 0511 | 0 | 50 |
| 0512 | 0 | 50 |
| 0513 | 0 | 50 |
| 0514 | 0 | 50 |
| 0515 | 0 | 50 |
| 0516 | 0 | 50 |
| 0517 | 0 | 50 |
| 0518 | 0 | 50 |
| 0519 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
