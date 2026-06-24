# Wikivoyage POI production run 0035

Processed batches: 0340-0349

## Result

- Rows reviewed: 500
- Accepted POIs: 117
- Rejected candidates: 383
- Cumulative rows reviewed: 17,450
- Cumulative accepted POIs: 7,246
- Cumulative rejected candidates: 10,204

One stray accepted file was removed during integration because the row had already been rejected:

- `northamerica/unitedstates/pennsylvania/reading/boyertown_museum_of_historic_vehicles.md`

One accepted file was converted to a reject during integration because it duplicated an existing POI under a destination alias:

- `northamerica/unitedstates/california/palo_alto/foothills_nature_preserve.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0340 | 6 | 44 |
| 0341 | 8 | 42 |
| 0342 | 10 | 40 |
| 0343 | 18 | 32 |
| 0344 | 9 | 41 |
| 0345 | 7 | 43 |
| 0346 | 16 | 34 |
| 0347 | 20 | 30 |
| 0348 | 12 | 38 |
| 0349 | 11 | 39 |

## Validation

- Frontmatter/body validator: `new_md 117 poi 117 sections 0 errors 0`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are distinct places.
