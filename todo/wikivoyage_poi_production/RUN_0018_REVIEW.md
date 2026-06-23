# Wikivoyage POI Production Run 0018

Processed batches: `0170` through `0179`

Rows processed: 500

Accepted POIs: 222

Rejected rows: 278

No section pages were added.

## Batch Counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0170 | 20 | 30 |
| 0171 | 29 | 21 |
| 0172 | 10 | 40 |
| 0173 | 22 | 28 |
| 0174 | 12 | 38 |
| 0175 | 17 | 33 |
| 0176 | 30 | 20 |
| 0177 | 27 | 23 |
| 0178 | 24 | 26 |
| 0179 | 31 | 19 |

## Integration Notes

Workers initially accepted 232 POIs and rejected 268 rows. Central review converted ten alias-path duplicates into rejects:

- `Mitre Peak` under `australiaandpacific/newzealand/south_island/otago/milford_sound`, duplicate of existing Milford Sound POI
- `Wassermann-bunker` under `europe/netherlands/waddenislands/schiermonnikoog_is`, duplicate of existing Schiermonnikoog POI
- `Jellyfish Lake` under `australiaandpacific/palau/rockislands`, duplicate of existing Koror POI
- `Ride a motorbike up the Hai Van Pass` under `asia/vietnam/danang`, duplicate of existing Hai Van Pass POI
- `Nergal Gate` under `asia/iraq/mosul`, duplicate of existing Ninevah POI
- `Cabo da Roca` under `europe/portugal/sintra`, duplicate of existing Cascais POI
- `Phu Phra Bat Historical Park` under `asia/thailand/nongkhai`, duplicate of existing Udon Thani POI
- `Grant-Kohrs Ranch National Historic Site` under `northamerica/unitedstates/montana/deer_lodge_1`, duplicate of existing Deer Lodge POI
- `Shimba Hills National Reserve` under `africa/kenya/thecoast/mombasa`, duplicate of existing South of Mombasa POI
- `Le Pont du Gard` under `europe/france/midi/languedoc/nmes`, duplicate of existing Nimes/Pont du Gard POI

Remaining global duplicate-title warnings were reviewed as distinct same-name places or generic names:

- `Catedral Metropolitana`
- `Cliff Walk`
- `Clock Tower`
- `Iglesia de San Pedro`
- `Jewish Cemetery`
- `Planes of Fame Air Museum`

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

Rows processed through batch `0179`: 8,950

Accepted POIs: 4,534

Rejected rows: 4,416
