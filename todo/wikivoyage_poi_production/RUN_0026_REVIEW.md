# Wikivoyage POI production run 0026

- Batches processed: `0250` through `0259`
- Rows processed: 500
- Accepted POIs: 118
- Rejected rows: 382
- Cumulative rows processed: 12,950
- Cumulative accepted POIs: 6,030
- Cumulative rejected rows: 6,920

## Batch counts

| Batch | Accepted | Rejected |
| --- | ---: | ---: |
| 0250 | 15 | 35 |
| 0251 | 17 | 33 |
| 0252 | 11 | 39 |
| 0253 | 12 | 38 |
| 0254 | 9 | 41 |
| 0255 | 12 | 38 |
| 0256 | 8 | 42 |
| 0257 | 13 | 37 |
| 0258 | 10 | 40 |
| 0259 | 11 | 39 |

## Integration notes

Central duplicate review converted seven initially accepted POIs into rejects:

- `Baofeng Lake` in `asia/china/hunan/zhangjiajie`, already covered under Wulingyuan.
- `Marmolada mountain massif` in `europe/italy/veneto/cortina_dampezzo`, already covered under Dolomites.
- `Martyrium` in `asia/turkey/pamukale`, already covered by the Martyrium of Saint Philip POI under Denizli.
- `Inishmurray` in `europe/ireland/sligo`, already covered under Rosses Point.
- `Bullers of Buchan` in `europe/unitedkingdom/scotland/peterhead`, already covered under Cruden Bay.
- `overview of Garganta del Diablo` in `southamerica/brazil/iguacufalls`, already covered under Puerto Iguazu.
- `Menhirs for Peace` in `europe/spain/northernspain/lacorua`, already covered under the Galicia/A Coruna path.

No global duplicate-title warnings remained after central duplicate conversion.

## Validation

- Frontmatter/body validator: 118 new POIs, 0 errors.
- Broken local link check: 0 broken links.
- Same-parent duplicate check: 0 duplicate groups.
- Global duplicate-title check: 0 duplicate groups.
- Django system check: passed.
