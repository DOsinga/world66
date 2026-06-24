# Wikivoyage POI production run 0036

Processed batches: 0350-0359

## Result

- Rows reviewed: 500
- Accepted POIs: 114
- Rejected candidates: 386
- Cumulative rows reviewed: 17,950
- Cumulative accepted POIs: 7,360
- Cumulative rejected candidates: 10,590

Six accepted files were converted to rejects during integration because they duplicated existing POIs under destination aliases:

- `asia/china/xinjiangprovince/burqin/kanas_lake.md`
- `europe/spain/galicia/vigo_city/santa_maria_de_castrelos.md`
- `europe/spain/northernspain/santiagodecompostela/pilgrimage_museum.md`
- `northamerica/unitedstates/california/sanjose/japantown.md`
- `northamerica/unitedstates/florida/panama_city_beach/pine_log_state_forest.md`
- `northamerica/unitedstates/florida/pensacola_beach/fort_pickens.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0350 | 7 | 43 |
| 0351 | 10 | 40 |
| 0352 | 12 | 38 |
| 0353 | 11 | 39 |
| 0354 | 7 | 43 |
| 0355 | 12 | 38 |
| 0356 | 15 | 35 |
| 0357 | 16 | 34 |
| 0358 | 13 | 37 |
| 0359 | 11 | 39 |

## Validation

- Frontmatter/body validator: `new_md 114 poi 114 sections 0 errors 0`
- Reject CSV schema/accounting: `headers_unique 1 bad_rows 0`, `reject_total 386`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are distinct places.
