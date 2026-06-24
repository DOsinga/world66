# Wikivoyage POI production run 0033

Processed batches: 0320-0329

## Result

- Rows reviewed: 500
- Accepted POIs: 116
- Rejected candidates: 384
- Cumulative rows reviewed: 16,450
- Cumulative accepted POIs: 7,053
- Cumulative rejected candidates: 9,397

Five accepted files were converted to rejects during integration because they duplicated existing POIs or duplicate destination aliases:

- `northamerica/unitedstates/alaska/anchorage/alaska_wildlife_conservation_center.md`
- `northamerica/unitedstates/california/longbeach/belmont_veterans_memorial_pier.md`
- `africa/sierraleone/freetown/bureh_beach.md`
- `asia/iran/mashhad/ferdowsi_mausoleum.md`
- `africa/sierraleone/freetown/tokeh_beach.md`

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0320 | 7 | 43 |
| 0321 | 10 | 40 |
| 0322 | 13 | 37 |
| 0323 | 7 | 43 |
| 0324 | 10 | 40 |
| 0325 | 15 | 35 |
| 0326 | 16 | 34 |
| 0327 | 16 | 34 |
| 0328 | 10 | 40 |
| 0329 | 12 | 38 |

## Validation

- Frontmatter/body validator: `new_md 116 poi 116 sections 0 errors 0`
- Broken local links: `broken_local_links 0`
- Django system check: `System check identified no issues (0 silenced).`
- Duplicate sweep: `dup_parent_groups 0`; remaining global title matches are distinct places.
