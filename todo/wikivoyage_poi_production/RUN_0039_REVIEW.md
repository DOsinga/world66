# Wikivoyage POI production run 0039

Processed batches: 0380-0389

## Result

- Rows reviewed: 500
- Accepted POIs: 35
- Rejected candidates: 465
- Cumulative rows reviewed: 19,450
- Cumulative accepted POIs: 7,548
- Cumulative rejected candidates: 11,902

The accepted set was small again, with most candidates rejected as minor commercial operators, transport-only listings, weak local venues, duplicate/covered context, or unlocatable low-confidence leads.

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0380 | 4 | 46 |
| 0381 | 5 | 45 |
| 0382 | 4 | 46 |
| 0383 | 4 | 46 |
| 0384 | 2 | 48 |
| 0385 | 4 | 46 |
| 0386 | 0 | 50 |
| 0387 | 5 | 45 |
| 0388 | 5 | 45 |
| 0389 | 2 | 48 |

## Validation

- Frontmatter/body validator: `new_md 35 poi 35 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 465`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are distinct places.
