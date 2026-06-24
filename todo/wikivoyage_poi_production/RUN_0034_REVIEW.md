# Wikivoyage POI production run 0034

Processed batches: 0330-0339

## Result

- Rows reviewed: 500
- Accepted POIs: 76
- Rejected candidates: 424
- Cumulative rows reviewed: 16,950
- Cumulative accepted POIs: 7,129
- Cumulative rejected candidates: 9,821

One accepted file was converted to a reject during integration because it duplicated an existing POI:

- `europe/unitedkingdom/england/leicester_nottingham_and_east_midlands/leicester/great_central_railway.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0330 | 5 | 45 |
| 0331 | 5 | 45 |
| 0332 | 4 | 46 |
| 0333 | 5 | 45 |
| 0334 | 10 | 40 |
| 0335 | 16 | 34 |
| 0336 | 4 | 46 |
| 0337 | 11 | 39 |
| 0338 | 8 | 42 |
| 0339 | 8 | 42 |

## Validation

- Frontmatter/body validator: `new_md 76 poi 76 sections 0 errors 0`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are distinct places.
