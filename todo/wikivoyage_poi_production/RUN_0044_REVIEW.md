# Wikivoyage POI production run 0044

Processed batches: 0430-0439

## Result

- Rows reviewed: 500
- Accepted POIs: 0
- Rejected candidates: 500
- Cumulative rows reviewed: 21,950
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 14,315

All ten batches in this wave were all-reject batches. Every row had a candidate score below the production threshold, and many also lacked coordinates or otherwise needed external sourcing before they could become usable POIs.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0430 | 0 | 50 |
| 0431 | 0 | 50 |
| 0432 | 0 | 50 |
| 0433 | 0 | 50 |
| 0434 | 0 | 50 |
| 0435 | 0 | 50 |
| 0436 | 0 | 50 |
| 0437 | 0 | 50 |
| 0438 | 0 | 50 |
| 0439 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 0 poi 0 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 500`
- Broken local links: `broken_local_links 0`
- Duplicate sweep: skipped because no POI markdown files were created.
