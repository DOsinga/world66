# Wikivoyage POI Production Run 0020

Processed batches: `0190` through `0199`

Rows processed: 500

Accepted POIs: 179

Rejected rows: 321

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0190 | 10 | 40 |
| 0191 | 18 | 32 |
| 0192 | 13 | 37 |
| 0193 | 14 | 36 |
| 0194 | 20 | 30 |
| 0195 | 21 | 29 |
| 0196 | 23 | 27 |
| 0197 | 27 | 23 |
| 0198 | 16 | 34 |
| 0199 | 17 | 33 |

## Integration Notes

Workers initially accepted 182 POIs and rejected 318 rows. Central review converted three duplicate rows into rejects:

- `Slains Castle` under `europe/unitedkingdom/scotland/peterhead`, duplicate of existing Cruden Bay POI
- `Cave of the Seven Sleepers` under `asia/turkey/ephesus`, duplicate of existing Selcuk POI
- `Diamond Peak` under `northamerica/unitedstates/nevada/reno`, duplicate of existing Lake Tahoe POI

Remaining global duplicate-title warnings were reviewed as distinct same-name places or generic names:

- `Cathedral of the Assumption of the Blessed Virgin Mary`
- `Church of the Dormition`
- `Grand Mosque`
- `Kailasanatha Temple`
- `Lake Park`
- `Market Square`
- `Museum of Natural History`
- `National Museum of Science and Technology`
- `Orchid Garden`
- `Palm Beach`
- `Queen's Park`
- `Sacred Heart of Jesus Cathedral`
- `St Nicholas Church`
- `St Paul's Church`
- `Wanshou Temple`
- `Waterfront Park`
- `White Island`
- `Woodward Park`

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

Rows processed through batch `0199`: 9,950

Accepted POIs: 4,825

Rejected rows: 5,125
