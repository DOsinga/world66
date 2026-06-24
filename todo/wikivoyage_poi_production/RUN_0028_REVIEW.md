# Wikivoyage POI production run 0028

Processed batches: 0270-0279

## Result

- Rows reviewed: 500
- Accepted POIs: 154
- Rejected candidates: 346
- Cumulative rows reviewed: 13,950
- Cumulative accepted POIs: 6,322
- Cumulative rejected candidates: 7,628

Three accepted files were converted to rejects during integration because they duplicated existing POIs under duplicate destination aliases:

- `northamerica/unitedstates/california/santa_barbara/arlington_theatre.md`
- `africa/egypt/cairo/abdeen_palace.md`
- `europe/belgium/ostende/sint_petrus_en_pauluskerk.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0270 | 16 | 34 |
| 0271 | 15 | 35 |
| 0272 | 15 | 35 |
| 0273 | 11 | 39 |
| 0274 | 18 | 32 |
| 0275 | 27 | 23 |
| 0276 | 14 | 36 |
| 0277 | 15 | 35 |
| 0278 | 14 | 36 |
| 0279 | 9 | 41 |

## Validation

- Frontmatter/body validator: `new_md 154 poi 154 sections 0 errors 0`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are same-name landmarks in different destinations.
