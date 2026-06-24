# Wikivoyage POI production run 0042

Processed batches: 0410-0419

## Result

- Rows reviewed: 500
- Accepted POIs: 14
- Rejected candidates: 486
- Cumulative rows reviewed: 20,950
- Cumulative accepted POIs: 7,615
- Cumulative rejected candidates: 13,335

Several batches in this wave were all-reject or near all-reject, mostly because the remaining candidates were below threshold, lacked usable coordinates, or were weak commercial/transport/listing leads.

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0410 | 3 | 47 |
| 0411 | 2 | 48 |
| 0412 | 0 | 50 |
| 0413 | 0 | 50 |
| 0414 | 3 | 47 |
| 0415 | 0 | 50 |
| 0416 | 0 | 50 |
| 0417 | 3 | 47 |
| 0418 | 2 | 48 |
| 0419 | 1 | 49 |

## Validation

- Frontmatter/body validator: `new_md 14 poi 14 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 486`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title match is a distinct place.
