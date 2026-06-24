# Wikivoyage POI production run 0043

Processed batches: 0420-0429

## Result

- Rows reviewed: 500
- Accepted POIs: 20
- Rejected candidates: 480
- Cumulative rows reviewed: 21,450
- Cumulative accepted POIs: 7,635
- Cumulative rejected candidates: 13,815

Batches 0426-0429 were all-reject batches. The remaining tail continues to be dominated by below-threshold, missing-coordinate, weak commercial, duplicate/covered, transport-only, or otherwise unfit candidates.

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0420 | 2 | 48 |
| 0421 | 4 | 46 |
| 0422 | 1 | 49 |
| 0423 | 3 | 47 |
| 0424 | 6 | 44 |
| 0425 | 4 | 46 |
| 0426 | 0 | 50 |
| 0427 | 0 | 50 |
| 0428 | 0 | 50 |
| 0429 | 0 | 50 |

## Validation

- Frontmatter/body validator: `new_md 20 poi 20 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 480`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`, `dup_title_groups 0`
