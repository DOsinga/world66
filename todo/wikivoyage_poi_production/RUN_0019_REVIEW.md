# Wikivoyage POI Production Run 0019

Processed batches: `0180` through `0189`

Rows processed: 500

Accepted POIs: 112

Rejected rows: 388

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0180 | 18 | 32 |
| 0181 | 11 | 39 |
| 0182 | 6 | 44 |
| 0183 | 10 | 40 |
| 0184 | 13 | 37 |
| 0185 | 11 | 39 |
| 0186 | 7 | 43 |
| 0187 | 12 | 38 |
| 0188 | 11 | 39 |
| 0189 | 13 | 37 |

## Integration Notes

Workers initially accepted 116 POIs and rejected 384 rows. Central review converted four duplicate rows into rejects:

- `Tiger Bay State Forest` under `northamerica/unitedstates/florida/ormond_beach`, duplicate of the accepted Daytona Beach row in this wave
- `Alpine Slide at Magic Mountain` under `northamerica/unitedstates/california/big_bear_lake`, duplicate of an existing legacy Big Bear Lake POI
- `Jamestown Settlement` under `northamerica/unitedstates/virginia/williamsburg`, duplicate of an existing Jamestown POI
- `Rengstorff House` under `northamerica/unitedstates/california/mountainvieuw`, duplicate of an existing Mountain View POI

Remaining global duplicate-title warnings were reviewed as distinct same-name places or generic names:

- `Casa da Cultura`
- `Oceanarium`
- `Orto Botanico`

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

Rows processed through batch `0189`: 9,450

Accepted POIs: 4,646

Rejected rows: 4,804
