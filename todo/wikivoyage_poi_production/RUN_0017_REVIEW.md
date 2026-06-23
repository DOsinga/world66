# Wikivoyage POI Production Run 0017

Processed batches: `0160` through `0169`

Rows processed: 500

Accepted POIs: 222

Rejected rows: 278

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0160 | 12 | 38 |
| 0161 | 16 | 34 |
| 0162 | 27 | 23 |
| 0163 | 29 | 21 |
| 0164 | 29 | 21 |
| 0165 | 20 | 30 |
| 0166 | 17 | 33 |
| 0167 | 18 | 32 |
| 0168 | 23 | 27 |
| 0169 | 31 | 19 |

## Integration Notes

Workers initially accepted 225 POIs and rejected 274 rows, with one additional unaccounted row in batch `0168`. Central review converted four rows into rejects:

- `斗南花卉市场夜间拍卖` under `asia/china/yunnanprovince/kunming`, no accepted POI file was created during worker duplicate/quality reconciliation
- `Adalaj Stepwell` under `asia/india/gujarat/gandhinagar`, duplicate of existing `asia/india/gujarat/ahmedabad/adalaj_stepwell`
- `Jaisamand Lake` under `asia/india/rajasthan/alwar`, duplicate of existing `asia/india/rajasthan/udaipur/jaisamand_lake`
- `Circus` under `europe/russia/ekaterinoburg`, duplicate alias-path candidate for `europe/russia/ural/ekaterinburg/yekaterinburg_circus`

Remaining global duplicate-title warnings were reviewed as distinct same-name places:

- `Big Buddha`
- `Fisherman's Wharf`
- `Franciscan Monastery`
- `Isla de Lobos`
- `Magnetic Hill`
- `Mana Island`
- `Mount Taylor`
- `Plaza Colon`
- `Red Hill`
- `Victory Square`
- `Water Tower`

Reject logs were normalized to the full candidate schema with `reject_reason`.

## Validation

- New POI frontmatter parses with `python-frontmatter`
- Required fields present: `title`, `type`, `latitude`, `longitude`, `tags`, `snippet`, `score`, `sources`
- `type: poi`, first tag `things_to_do`, valid coordinates, scores at least 6
- Bodies have at least two paragraphs
- No broken local markdown links in new files
- No same-parent duplicate POI titles
- Django system check passed

## Cumulative Production Totals

Rows processed through batch `0169`: 8,450

Accepted POIs: 4,312

Rejected rows: 4,138
