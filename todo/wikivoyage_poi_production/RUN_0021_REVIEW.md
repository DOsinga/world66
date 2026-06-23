# Wikivoyage POI Production Run 0021

Processed batches: `0200` through `0209`

Rows processed: 500

Accepted POIs: 191

Rejected rows: 309

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0200 | 14 | 36 |
| 0201 | 18 | 32 |
| 0202 | 18 | 32 |
| 0203 | 15 | 35 |
| 0204 | 11 | 39 |
| 0205 | 13 | 37 |
| 0206 | 21 | 29 |
| 0207 | 26 | 24 |
| 0208 | 29 | 21 |
| 0209 | 26 | 24 |

## Integration Notes

Workers initially accepted 199 POIs and rejected 301 rows. Central review converted eight duplicate rows into rejects:

- `Derinkuyu` under `asia/turkey/cappadocia/nevsehir`, duplicate of existing Derinkuyu Underground City POI
- `Buffalo Trace` under `northamerica/unitedstates/kentucky/lexington`, duplicate of existing Frankfort POI
- `Debrigadh Willife Sanctury` under `asia/india/orissa/sambalpur`, duplicate of existing Bargarh POI
- `Sand Dollar Beach` under `northamerica/unitedstates/california/big_sur`, duplicate of the accepted established Big Sur path in this wave
- `Huanglong Cave` under `asia/china/hunan/zhangjiajie`, duplicate of existing Wulingyuan POI
- `Mt. Kanla-on Natural Park` under `asia/philippines/negrosisland/bacolod`, duplicate of existing Kabankalan City POI
- `Queenston Heights Park` under `northamerica/canada/ontario/niagrafalls`, duplicate of existing Niagara-on-the-Lake POI
- `California's Great America` under `northamerica/unitedstates/california/sanjose`, duplicate of existing San Jose/Santa Clara coverage

Remaining global duplicate-title warnings were reviewed as distinct same-name places or generic names:

- `City Museum`
- `Melrose House`
- `Natural Bridge`
- `St Nicholas Cathedral`
- `St Patrick's Church`
- `State Theatre`

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

Rows processed through batch `0209`: 10,450

Accepted POIs: 5,016

Rejected rows: 5,434
