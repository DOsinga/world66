# Wikivoyage POI production run 0038

Processed batches: 0370-0379

## Result

- Rows reviewed: 500
- Accepted POIs: 35
- Rejected candidates: 465
- Cumulative rows reviewed: 18,950
- Cumulative accepted POIs: 7,513
- Cumulative rejected candidates: 11,437

This shard had a low yield, with many remaining candidates rejected as minor commercial operators, transport-only listings, weak local venues, duplicate/covered context, or unlocatable low-confidence leads.

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0370 | 6 | 44 |
| 0371 | 3 | 47 |
| 0372 | 3 | 47 |
| 0373 | 3 | 47 |
| 0374 | 3 | 47 |
| 0375 | 6 | 44 |
| 0376 | 6 | 44 |
| 0377 | 3 | 47 |
| 0378 | 1 | 49 |
| 0379 | 1 | 49 |

## Validation

- Frontmatter/body validator: `new_md 35 poi 35 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 465`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`, `dup_title_groups 0`
