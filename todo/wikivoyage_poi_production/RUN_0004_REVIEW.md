# Wikivoyage POI Production Run 0004

Processed batches:

- `batch_0030.csv` through `batch_0039.csv`

Outcome:

- Accepted as POIs: 312
- Rejected: 188
- Added helper section files: 0
- Acceptance rate: 62.4%

Batch totals:

- Batch 0030: 27 accepted, 23 rejected
- Batch 0031: 35 accepted, 15 rejected
- Batch 0032: 19 accepted, 31 rejected
- Batch 0033: 24 accepted, 26 rejected
- Batch 0034: 36 accepted, 14 rejected
- Batch 0035: 34 accepted, 16 rejected
- Batch 0036: 24 accepted, 26 rejected
- Batch 0037: 27 accepted, 23 rejected
- Batch 0038: 41 accepted, 9 rejected
- Batch 0039: 45 accepted, 5 rejected

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
