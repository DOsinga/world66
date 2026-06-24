# Wikivoyage POI production run 0037

Processed batches: 0360-0369

## Result

- Rows reviewed: 500
- Accepted POIs: 118
- Rejected candidates: 382
- Cumulative rows reviewed: 18,450
- Cumulative accepted POIs: 7,478
- Cumulative rejected candidates: 10,972

Two accepted files were converted to rejects during integration because they duplicated existing POIs under destination aliases:

- `asia/turkey/pamukale/basilica_baths.md`
- `europe/spain/galicia/santiagodecompostela/the_two_marias.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0360 | 18 | 32 |
| 0361 | 25 | 25 |
| 0362 | 9 | 41 |
| 0363 | 16 | 34 |
| 0364 | 7 | 43 |
| 0365 | 8 | 42 |
| 0366 | 12 | 38 |
| 0367 | 16 | 34 |
| 0368 | 6 | 44 |
| 0369 | 1 | 49 |

## Validation

- Frontmatter/body validator: `new_md 118 poi 118 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 382`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are distinct places.
