# Wikivoyage POI production run 0060

Processed batches: 0590-0599

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 29,950
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 22,315

All ten batches in this final wave were all-reject batches. Every row had a candidate score of 0.47, below the production threshold, so no POI markdown files were created.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0590 | 0 | 50 |
| 0591 | 0 | 50 |
| 0592 | 0 | 50 |
| 0593 | 0 | 50 |
| 0594 | 0 | 50 |
| 0595 | 0 | 50 |
| 0596 | 0 | 50 |
| 0597 | 0 | 50 |
| 0598 | 0 | 50 |
| 0599 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
