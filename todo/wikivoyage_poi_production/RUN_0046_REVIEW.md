# Wikivoyage POI production run 0046

Processed batches: 0450-0459

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 22,950
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 15,315

All ten batches in this wave were all-reject batches. Every row had a candidate score below the production threshold, so no POI markdown files were created.

The initial reject files for batches 0450 and 0451 used a shortened reject schema. They were regenerated from the source batch rows with the full production reject schema before validation and commit.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0450 | 0 | 50 |
| 0451 | 0 | 50 |
| 0452 | 0 | 50 |
| 0453 | 0 | 50 |
| 0454 | 0 | 50 |
| 0455 | 0 | 50 |
| 0456 | 0 | 50 |
| 0457 | 0 | 50 |
| 0458 | 0 | 50 |
| 0459 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
