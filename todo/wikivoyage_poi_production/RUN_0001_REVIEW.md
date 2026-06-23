# Wikivoyage POI Production Run 0001

Processed batches:

- `batch_0001.csv`
- `batch_0002.csv`
- `batch_0003.csv`
- `batch_0004.csv`
- `batch_0005.csv`

Outcome:

- Accepted as POIs: 210
- Rejected: 40
- Added helper section files: 6
- Acceptance rate: 84.0%

Batch totals:

- Batch 0001: 37 accepted, 13 rejected
- Batch 0002: 43 accepted, 7 rejected
- Batch 0003: 39 accepted, 11 rejected
- Batch 0004: 46 accepted, 4 rejected
- Batch 0005: 45 accepted, 5 rejected

Central review adjustment:

- Removed `southamerica/argentina/iguazufalls/parque_das_aves.md` after
  merge review. The candidate was a duplicate/wrong-side listing; the accepted
  Brazil-side POI at `southamerica/brazil/iguacufalls/parque_das_aves.md` is
  the correct placement.

Validation:

- All new POI frontmatter parses with `python-frontmatter`.
- All new POIs have required fields.
- All new POIs have valid coordinates.
- All new POIs have score `>= 6.0`.
- All new POIs have `things_to_do` as the first tag.
- All new POIs have sources and at least two body paragraphs.
- No duplicate new POI titles remain within the same parent location.
- New content files introduce no broken internal markdown links.
- `python manage.py check` passes.
