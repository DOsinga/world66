# Wikivoyage POI Production Run 0003

Processed batches:

- `batch_0010.csv` through `batch_0029.csv`

Outcome:

- Accepted as POIs: 712
- Rejected: 288
- Added helper section files: 0
- Acceptance rate: 71.2%

Batch totals:

- Batch 0010: 40 accepted, 10 rejected
- Batch 0011: 41 accepted, 9 rejected
- Batch 0012: 20 accepted, 30 rejected
- Batch 0013: 23 accepted, 27 rejected
- Batch 0014: 13 accepted, 37 rejected
- Batch 0015: 10 accepted, 40 rejected
- Batch 0016: 46 accepted, 4 rejected
- Batch 0017: 45 accepted, 5 rejected
- Batch 0018: 38 accepted, 12 rejected
- Batch 0019: 39 accepted, 11 rejected
- Batch 0020: 45 accepted, 5 rejected
- Batch 0021: 39 accepted, 11 rejected
- Batch 0022: 41 accepted, 9 rejected
- Batch 0023: 36 accepted, 14 rejected
- Batch 0024: 43 accepted, 7 rejected
- Batch 0025: 38 accepted, 12 rejected
- Batch 0026: 40 accepted, 10 rejected
- Batch 0027: 39 accepted, 11 rejected
- Batch 0028: 39 accepted, 11 rejected
- Batch 0029: 37 accepted, 13 rejected

Validation:

- All new POI frontmatter parses with `python-frontmatter`.
- All new POIs have required fields.
- All new POIs have valid coordinates.
- All new POIs have score `>= 6.0`.
- All new POIs have `things_to_do` as the first tag.
- All new POIs have sources and at least two body paragraphs.
- No duplicate new POI titles found within the same parent location.
- New content files introduce no broken internal markdown links.
- `python manage.py check` passes.
