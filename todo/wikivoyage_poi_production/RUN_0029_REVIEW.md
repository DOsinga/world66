# Wikivoyage POI production run 0029

Processed batches: 0280-0289

## Result

- Rows reviewed: 500
- Accepted POIs: 176
- Rejected candidates: 324
- Cumulative rows reviewed: 14,450
- Cumulative accepted POIs: 6,498
- Cumulative rejected candidates: 7,952

Three accepted files were converted to rejects during integration because they duplicated existing POIs under duplicate destination aliases:

- `asia/india/maharashtra/alibag/revdanda_fort.md`
- `asia/india/maharashtra/alibaug/revdanda_fort.md`
- `europe/armenia/garni/geghard_monastery.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0280 | 18 | 32 |
| 0281 | 17 | 33 |
| 0282 | 16 | 34 |
| 0283 | 19 | 31 |
| 0284 | 23 | 27 |
| 0285 | 22 | 28 |
| 0286 | 3 | 47 |
| 0287 | 5 | 45 |
| 0288 | 24 | 26 |
| 0289 | 29 | 21 |

## Validation

- Frontmatter/body validator: `new_md 176 poi 176 sections 0 errors 0`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are same-name landmarks in different destinations.
