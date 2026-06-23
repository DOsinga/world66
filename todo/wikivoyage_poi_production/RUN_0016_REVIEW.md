# Wikivoyage POI Production Run 0016

Processed batches: `0150` through `0159`

Rows processed: 500

Accepted POIs: 220

Rejected rows: 280

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0150 | 25 | 25 |
| 0151 | 36 | 14 |
| 0152 | 19 | 31 |
| 0153 | 20 | 30 |
| 0154 | 19 | 31 |
| 0155 | 17 | 33 |
| 0156 | 22 | 28 |
| 0157 | 25 | 25 |
| 0158 | 16 | 34 |
| 0159 | 21 | 29 |

## Integration Notes

Workers initially accepted 223 POIs and rejected 277 rows. Central duplicate review converted three accepted POIs into rejects:

- `Castelo Do Queijo` under `europe/portugal/oporto`, duplicate of existing `europe/portugal/porto/castelo_do_queijo`
- `Khao Kanab Nam` under `asia/thailand/krabi/krabitown`, duplicate of existing `asia/thailand/krabi/khao_kanab_nam`
- `Shamash Gate` under `asia/iraq/mosul`, duplicate of existing `asia/iraq/ninevah/shamash_gate`

Remaining global duplicate-title warnings were reviewed as distinct same-name places:

- `Echo Point`
- `Jardin des Plantes`
- `Jewish Cemetery`
- `Masjid al Qiblatayn`
- `Old Jewish Cemetery`
- `Plaza 25 de Mayo`
- `Triumphal Arch`
- `Victory Square`

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

Rows processed through batch `0159`: 7,950

Accepted POIs: 4,090

Rejected rows: 3,860
