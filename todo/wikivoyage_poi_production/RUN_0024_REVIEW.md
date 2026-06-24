# Wikivoyage POI production run 0024

- Batches processed: `0230` through `0239`
- Rows processed: 500
- Accepted POIs: 209
- Rejected rows: 291
- Cumulative rows processed: 11,950
- Cumulative accepted POIs: 5,753
- Cumulative rejected rows: 6,197

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0230 | 29 | 21 |
| 0231 | 29 | 21 |
| 0232 | 23 | 27 |
| 0233 | 22 | 28 |
| 0234 | 13 | 37 |
| 0235 | 12 | 38 |
| 0236 | 19 | 31 |
| 0237 | 23 | 27 |
| 0238 | 19 | 31 |
| 0239 | 20 | 30 |

## Integration notes

Central duplicate review converted four initially accepted POIs into rejects:

- `Japanese American Museum of San Jose` in `northamerica/unitedstates/california/san_jose`, already covered under the canonical San Jose path.
- `Pont de Normandie` in `europe/france/normandybrittany/lehavre`, already covered under Honfleur.
- `Summit Tunnel` in `europe/unitedkingdom/england/manchester_liverpool_and_north_west/rochdale`, already covered under Todmorden.
- `Rock carving area of Aspeberget` in `europe/sweden/tanum`, already covered by the existing Aspeberget Rock Carvings POI in Tanum.

Remaining global duplicate-title warnings were reviewed as distinct same-name places or generic names in different destinations:

- `Blue Reef Aquarium`
- `Greek Theatre`
- `Klinger Lake`
- `La Cala`
- `La Gruta`
- `Lion Gate`
- `Meeting of the Waters`
- `Museo de Historia Natural`
- `Old Harbour`
- `Torre dell Orologio`

## Validation

- Frontmatter/body validator: 209 new POIs, 0 errors.
- Broken local link check: 0 broken links.
- Same-parent duplicate check: 0 duplicate groups.
- Django system check: passed.
