# Wikivoyage POI production run 0041

Processed batches: 0400-0409

## Result

- Rows reviewed: 500
- Accepted POIs: 20
- Rejected candidates: 480
- Cumulative rows reviewed: 20,450
- Cumulative accepted POIs: 7,601
- Cumulative rejected candidates: 12,849

Batches 0406 and 0407 were both all-reject batches. The tail is now heavily dominated by below-threshold, missing-coordinate, weak commercial, duplicate, transport-only, or otherwise unfit candidates.

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0400 | 4 | 46 |
| 0401 | 6 | 44 |
| 0402 | 1 | 49 |
| 0403 | 2 | 48 |
| 0404 | 2 | 48 |
| 0405 | 1 | 49 |
| 0406 | 0 | 50 |
| 0407 | 0 | 50 |
| 0408 | 2 | 48 |
| 0409 | 2 | 48 |

## Validation

- Frontmatter/body validator: `new_md 20 poi 20 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 480`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title match is a distinct place.
