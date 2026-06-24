# Wikivoyage POI production run 0040

Processed batches: 0390-0399

## Result

- Rows reviewed: 500
- Accepted POIs: 33
- Rejected candidates: 467
- Cumulative rows reviewed: 19,950
- Cumulative accepted POIs: 7,581
- Cumulative rejected candidates: 12,369

One worker stalled on batches 0396-0397 before writing output. It was closed and the two batches were reassigned cleanly; the replacement worker completed them with 4 accepted POIs and 96 rejects.

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0390 | 0 | 50 |
| 0391 | 3 | 47 |
| 0392 | 3 | 47 |
| 0393 | 6 | 44 |
| 0394 | 6 | 44 |
| 0395 | 2 | 48 |
| 0396 | 1 | 49 |
| 0397 | 3 | 47 |
| 0398 | 4 | 46 |
| 0399 | 5 | 45 |

## Validation

- Frontmatter/body validator: `new_md 33 poi 33 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 467`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title match is a distinct place.
