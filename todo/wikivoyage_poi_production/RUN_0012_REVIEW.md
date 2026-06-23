# Wikivoyage POI Production Run 0012

Processed batches: `0110` through `0119`

Rows processed: 500

Accepted POIs: 158

Rejected rows: 342

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0110 | 26 | 24 |
| 0111 | 27 | 23 |
| 0112 | 8 | 42 |
| 0113 | 10 | 40 |
| 0114 | 13 | 37 |
| 0115 | 25 | 25 |
| 0116 | 16 | 34 |
| 0117 | 12 | 38 |
| 0118 | 7 | 43 |
| 0119 | 14 | 36 |

## Integration Notes

Workers initially accepted 164 POIs and rejected 336 rows. Central duplicate review converted six accepted POIs into rejects:

- `Akab' Dzib` under `northamerica/mexico/yucatan/chichen_itza`, duplicate of existing `northamerica/mexico/chichenitza/akab_dzib`
- `Bharat Mandir` under `asia/india/uttaranchal/rishikesh`, duplicate alias-path candidate in this wave
- `Bharat Mandir` under `asia/india/uttarpradesh/rishikesh`, duplicate alias-path candidate in this wave
- `Kihim Beach` under `asia/india/alibaug`, duplicate of existing Alibag/Alibaug POIs
- `Salt Canyons` under `africa/ethiopia/danakilsdepression`, duplicate of existing Danakil salt-canyon POI
- `Smbataberd Fortress` under `europe/armenia/vayots_dzor_marz/yeghegnadzor`, duplicate of existing `europe/armenia/vayots_dzor_marz/smbataberd_fortres`

Remaining global duplicate-title warnings were reviewed as distinct same-name places:

- `Alexander Nevsky Cathedral`
- `British Cemetery`
- `Sri Mariamman Temple`

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

Rows processed through batch `0119`: 5,950

Accepted POIs: 3,210

Rejected rows: 2,740
