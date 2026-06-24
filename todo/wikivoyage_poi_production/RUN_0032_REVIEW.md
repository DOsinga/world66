# Wikivoyage POI production run 0032

Processed batches: 0310-0319

## Result

- Rows reviewed: 500
- Accepted POIs: 108
- Rejected candidates: 392
- Cumulative rows reviewed: 15,950
- Cumulative accepted POIs: 6,937
- Cumulative rejected candidates: 9,013

One accepted file was converted to a reject during integration because it duplicated an existing POI:

- `asia/jordan/madaba/wadi_mujib.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0310 | 12 | 38 |
| 0311 | 11 | 39 |
| 0312 | 12 | 38 |
| 0313 | 10 | 40 |
| 0314 | 9 | 41 |
| 0315 | 10 | 40 |
| 0316 | 9 | 41 |
| 0317 | 8 | 42 |
| 0318 | 12 | 38 |
| 0319 | 15 | 35 |

## Validation

- Frontmatter/body validator: `new_md 108 poi 108 sections 0 errors 0`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are distinct places.
