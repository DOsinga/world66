# Wikivoyage POI Production Run 0007

Processed batches: `0060` through `0069`

## Result

- Rows processed: 500
- Accepted POIs: 206
- Rejected rows: 294
- Section files added: 0

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0060 | 18 | 32 |
| 0061 | 21 | 29 |
| 0062 | 22 | 28 |
| 0063 | 23 | 27 |
| 0064 | 29 | 21 |
| 0065 | 30 | 20 |
| 0066 | 10 | 40 |
| 0067 | 16 | 34 |
| 0068 | 15 | 35 |
| 0069 | 22 | 28 |

## Validation

- Frontmatter parse and required POI fields: passed
- Coordinate bounds and `score >= 6`: passed
- First tag `things_to_do`: passed
- Sources present and at least two body paragraphs: passed
- Duplicate title under same parent: none found
- Broken local markdown links in new files: none found
- Django system check: passed

## Notes

Nine initially accepted rows were converted to rejections after a global duplicate-title pass found they duplicated existing World66 POIs across neighboring or alias location paths:

- Castletown House
- Cenote Ik Kil
- Ettal Abbey
- Lick Observatory
- Safari West
- Somerleyton Hall
- The Blue Room
- Zelve Open Air Museum
- Ozkonak Underground City

The remaining global title matches are different places with shared names: Tin City, Trinity College, and Victoria Hall.

Cumulative production total after this run: 3,450 rows processed, 2,230 accepted POIs, 1,220 rejected rows.
