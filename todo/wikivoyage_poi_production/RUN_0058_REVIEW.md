# Wikivoyage POI production run 0058

Processed batches: 0570-0579

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 28,950
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 21,315

All ten batches in this wave were all-reject batches. Every row had a candidate score below the production threshold, so no POI markdown files were created.

Most of the wave remained at a candidate score of 0.51; the tail of the wave included candidates down to 0.48.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0570 | 0 | 50 |
| 0571 | 0 | 50 |
| 0572 | 0 | 50 |
| 0573 | 0 | 50 |
| 0574 | 0 | 50 |
| 0575 | 0 | 50 |
| 0576 | 0 | 50 |
| 0577 | 0 | 50 |
| 0578 | 0 | 50 |
| 0579 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
