# Wikivoyage POI production run 0023

- Batches processed: `0220` through `0229`
- Rows processed: 500
- Accepted POIs: 235
- Rejected rows: 265
- Cumulative rows processed: 11,450
- Cumulative accepted POIs: 5,544
- Cumulative rejected rows: 5,906

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0220 | 31 | 19 |
| 0221 | 26 | 24 |
| 0222 | 22 | 28 |
| 0223 | 24 | 26 |
| 0224 | 24 | 26 |
| 0225 | 30 | 20 |
| 0226 | 16 | 34 |
| 0227 | 20 | 30 |
| 0228 | 20 | 30 |
| 0229 | 22 | 28 |

## Integration notes

Central duplicate review converted three initially accepted POIs into rejects:

- `Sea Life Sunshine Coast` in `australiaandpacific/australia/queensland/sunshinecoast`, already covered under Mooloolaba/Maroochydore.
- `Santa Barbara Zoo` in `northamerica/unitedstates/california/santa_barbara`, already covered under the canonical Santa Barbara path.
- `Heritage Rose Garden` in `northamerica/unitedstates/california/san_jose`, already covered under the canonical San Jose path.

Remaining global duplicate-title warnings were reviewed as distinct same-name places or generic names in different destinations:

- `Bajrakli Mosque`
- `Botanical Garden`
- `Cathedral of Saint John the Baptist`
- `Church of the Assumption`
- `Church of the Immaculate Conception`
- `Ethnographic Museum`
- `Fort Amsterdam`
- `Fox Theater`
- `Museum of Anthropology`
- `Nanshan Park`
- `Pharmacy Museum`
- `Santa Chiara`
- `Saryan Museum`
- `St John's Church`
- `Theatre Royal`
- `Washington Park`
- `Waterfront Park`

## Validation

- Frontmatter/body validator: 235 new POIs, 0 errors.
- Broken local link check: 0 broken links.
- Same-parent duplicate check: 0 duplicate groups.
- Django system check: passed.
