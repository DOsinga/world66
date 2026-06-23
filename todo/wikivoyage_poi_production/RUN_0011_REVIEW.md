# Wikivoyage POI Production Run 0011

Processed batches: `0100` through `0109`

Rows processed: 500

Accepted POIs: 200

Rejected rows: 300

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0100 | 33 | 17 |
| 0101 | 27 | 23 |
| 0102 | 17 | 33 |
| 0103 | 21 | 29 |
| 0104 | 23 | 27 |
| 0105 | 19 | 31 |
| 0106 | 17 | 33 |
| 0107 | 19 | 31 |
| 0108 | 12 | 38 |
| 0109 | 12 | 38 |

## Integration Notes

Workers initially accepted 203 POIs and rejected 297 rows. Central duplicate review converted three accepted POIs into rejects:

- `Bruce's Beach` under `northamerica/unitedstates/california/manhattenbeach`, duplicate of existing `northamerica/unitedstates/california/manhattan_beach/bruces_beach`
- `Haghpat Monastery` under `europe/armenia/alaverdi`, duplicate of existing `europe/armenia/haghpat/haghpat_monastery`
- `Observation Point` under `northamerica/unitedstates/utah/zion`, duplicate of existing `northamerica/unitedstates/utah/springdale/observation_point`

Remaining global duplicate-title warnings were reviewed as distinct same-name places:

- `Cathedral of St George`
- `City Park`
- `Great Wall Museum`
- `Pefkos Beach`
- `Projeto Tamar`
- `St Andrew's Kirk`
- `St Michael's Cathedral`
- `St Peter's Church`
- `Torre del Moro`
- `Veterans Park`
- `Victory Park`

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

Rows processed through batch `0109`: 5,450

Accepted POIs: 3,052

Rejected rows: 2,398
