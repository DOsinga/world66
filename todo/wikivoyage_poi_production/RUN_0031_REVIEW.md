# Wikivoyage POI production run 0031

Processed batches: 0300-0309

## Result

- Rows reviewed: 500
- Accepted POIs: 174
- Rejected candidates: 326
- Cumulative rows reviewed: 15,450
- Cumulative accepted POIs: 6,829
- Cumulative rejected candidates: 8,621

One accepted file was converted to a reject during integration because it duplicated an existing POI in the same destination:

- `africa/ethiopia/axum/ezana_tablet.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0300 | 9 | 41 |
| 0301 | 28 | 22 |
| 0302 | 16 | 34 |
| 0303 | 20 | 30 |
| 0304 | 20 | 30 |
| 0305 | 13 | 37 |
| 0306 | 18 | 32 |
| 0307 | 19 | 31 |
| 0308 | 15 | 35 |
| 0309 | 16 | 34 |

## Validation

- Frontmatter/body validator: `new_md 174 poi 174 sections 0 errors 0`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are same-name landmarks in different destinations.
