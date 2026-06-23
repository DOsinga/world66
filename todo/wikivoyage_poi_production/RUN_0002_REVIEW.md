# Wikivoyage POI Production Run 0002

Processed batches:

- `batch_0006.csv`
- `batch_0007.csv`
- `batch_0008.csv`
- `batch_0009.csv`

Outcome:

- Accepted as POIs: 117
- Rejected: 83
- Added helper section files: 6
- Acceptance rate: 58.5%

Batch totals:

- Batch 0006: 31 accepted, 19 rejected
- Batch 0007: 29 accepted, 21 rejected
- Batch 0008: 25 accepted, 25 rejected
- Batch 0009: 32 accepted, 18 rejected

Validation:

- All new POI frontmatter parses with `python-frontmatter`.
- All new POIs have required fields.
- All new POIs have valid coordinates.
- All new POIs have score `>= 6.0`.
- All new POIs have `things_to_do` as the first tag.
- All new POIs have sources and at least two body paragraphs.
- No duplicate new POI titles found within the same parent location.
- New content files introduce no broken internal markdown links.
