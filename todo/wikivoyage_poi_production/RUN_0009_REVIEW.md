# Wikivoyage POI Production Run 0009

Processed batches: `0080` through `0089`

Rows processed: 500

Accepted POIs: 223

Rejected rows: 277

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0080 | 12 | 38 |
| 0081 | 26 | 24 |
| 0082 | 20 | 30 |
| 0083 | 27 | 23 |
| 0084 | 19 | 31 |
| 0085 | 31 | 19 |
| 0086 | 27 | 23 |
| 0087 | 31 | 19 |
| 0088 | 16 | 34 |
| 0089 | 14 | 36 |

## Integration Notes

Workers initially accepted 228 POIs and rejected 272 rows. Central duplicate review converted five accepted POIs into rejects:

- `Cenote Ik Kil`, duplicate of existing `northamerica/mexico/cancun/cenote_ik_kil`
- `She Changes`, duplicate of existing `europe/portugal/porto/she_changes`
- `Cleeve Abbey`, duplicate of existing `.../minehead/cleeve_abbey`
- `Golden Whip Stream`, duplicate of existing `asia/china/hunan/wulingyuan/golden_whip_stream`
- `Home of Rest for Old Horses` under `europe/unitedkingdom/manisleof/douglas`, duplicate of the accepted `europe/isleofman/douglas` copy

Remaining global duplicate-title warnings were reviewed as distinct same-name or same-category places:

- `Cave of the Seven Sleepers`
- `Museum of Fine Arts`
- `Royal Botanic Gardens`
- `Sacred Heart Cathedral`
- `St Catherine's Church`
- `St Francis of Assisi Church`
- `Valle de la Luna`
- `Watertoren`

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

Rows processed through batch `0089`: 4,450

Accepted POIs: 2,682

Rejected rows: 1,768
