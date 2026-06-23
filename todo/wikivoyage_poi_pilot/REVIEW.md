# Wikivoyage POI Pilot Review

Pilot input: 250 filtered high-confidence Wikivoyage `see`/`do` candidates.

## Outcome

- Accepted as POIs: 134
- Rejected: 116
- Added helper section files: 3
- Acceptance rate: 53.6%

## Validation

Automated checks on the new content files:

- All new POI frontmatter parses with `python-frontmatter`.
- All new POIs have `title`, `type: poi`, `latitude`, `longitude`, `tags`,
  `snippet`, `score`, and `sources`.
- All new POIs have score `>= 6.0`.
- All new POIs have `things_to_do` as the first tag.
- All new POIs have coordinates in valid latitude/longitude ranges.
- All new POIs have at least two body paragraphs.
- New content files introduce no broken internal markdown links.
- No exact long Wikivoyage candidate-description snippets were found in new
  POI bodies.
- No trailing whitespace found in new content files.

Full repo linter still reports pre-existing broken links elsewhere in the
tree, so it is not clean as a global signal for this pilot.

## Quality Notes

The source looks useful. The strongest yield is for sights, museums,
monuments, religious architecture, parks, waterfalls, archaeological sites,
memorials, and day-trip nature stops. The reject logs show the filter is still
letting through duplicates, wrong-location candidates, inaccessible venues,
and ordinary service/commercial rows, but the agents rejected many of those
correctly.

Main follow-up risk: 35 accepted POIs have only Wikivoyage and/or OSM in their
`sources`. That is acceptable for this pilot review but should be tightened
before scaling the workflow.

Some accepted rows are day-trip scale rather than central city POIs. They are
useful travel content, but a later cleanup pass may choose to promote some of
them to locations or linked day-trip destinations.

## Batch Totals

- Batch 01: 26 accepted, 24 rejected
- Batch 02: 30 accepted, 20 rejected
- Batch 03: 26 accepted, 24 rejected
- Batch 04: 29 accepted, 21 rejected
- Batch 05: 23 accepted after review, 27 rejected after review

Batch 05 originally accepted Lake Bakili; review removed it as too obscure and
geographically/source ambiguous for the Eritrea Danakil parent.
