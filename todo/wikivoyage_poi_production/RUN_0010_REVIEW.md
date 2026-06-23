# Wikivoyage POI Production Run 0010

Processed batches: `0090` through `0099`

Rows processed: 500

Accepted POIs: 170

Rejected rows: 330

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0090 | 14 | 36 |
| 0091 | 14 | 36 |
| 0092 | 10 | 40 |
| 0093 | 12 | 38 |
| 0094 | 18 | 32 |
| 0095 | 21 | 29 |
| 0096 | 20 | 30 |
| 0097 | 24 | 26 |
| 0098 | 17 | 33 |
| 0099 | 20 | 30 |

## Integration Notes

Workers initially accepted 171 POIs and rejected 329 rows. Central duplicate review converted one accepted POI into a reject:

- `Longgang Mosque` under `asia/taiwan/taoyuan`, duplicate of existing `asia/taiwan/jungli/longgang_mosque`

Remaining global duplicate-title warnings were reviewed as distinct same-name places:

- `Bharat Mata Mandir`
- `Castillo de San Felipe`
- `Cathedral of Our Lady of the Rosary`
- `Iglesia San Jose`
- `Jama Masjid`
- `Long Beach`
- `Museum of Archaeology`
- `Museum of Modern Art`
- `People's Park`
- `Place des Martyrs`
- `Washington Park`
- `Wat Si Chum`

Reject logs were normalized to the full candidate schema with `reject_reason`.

This run had a lower acceptance rate than prior waves because several rows were local parks, beaches, event venues, commercial operators, weakly sourced minor religious sites, distant day-trip destinations, or access/currentness-sensitive leads that did not clear the production bar.

## Validation

- New POI frontmatter parses with `python-frontmatter`
- Required fields present: `title`, `type`, `latitude`, `longitude`, `tags`, `snippet`, `score`, `sources`
- `type: poi`, first tag `things_to_do`, valid coordinates, scores at least 6
- Bodies have at least two paragraphs
- No broken local markdown links in new files
- No same-parent duplicate POI titles
- Django system check passed

## Cumulative Production Totals

Rows processed through batch `0099`: 4,950

Accepted POIs: 2,852

Rejected rows: 2,098
