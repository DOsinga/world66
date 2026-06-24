# Wikivoyage POI production run 0030

Processed batches: 0290-0299

## Result

- Rows reviewed: 500
- Accepted POIs: 157
- Rejected candidates: 343
- Cumulative rows reviewed: 14,950
- Cumulative accepted POIs: 6,655
- Cumulative rejected candidates: 8,295

Two accepted files were converted to rejects during integration because they duplicated existing POIs:

- `europe/spain/basque_country_euskadi/bilbao/vizcaya_bridge.md`
- `northamerica/unitedstates/california/centralcoast/santabarbara/leadbetter_beach.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0290 | 9 | 41 |
| 0291 | 14 | 36 |
| 0292 | 16 | 34 |
| 0293 | 19 | 31 |
| 0294 | 11 | 39 |
| 0295 | 12 | 38 |
| 0296 | 22 | 28 |
| 0297 | 22 | 28 |
| 0298 | 15 | 35 |
| 0299 | 17 | 33 |

## Validation

- Frontmatter/body validator: `new_md 157 poi 157 sections 0 errors 0`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are same-name landmarks in different destinations.
