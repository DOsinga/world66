# Wikivoyage Coverage Map

`tools/wikivoyage_coverage.py` builds a local SQLite database for comparing
World66 destination and POI coverage against Wikivoyage. It is meant for gap
analysis, not direct content import.

Wikivoyage is useful here because it is explicitly travel-oriented and its
listings are structured by travel sections (`See`, `Do`, `Eat`, `Drink`,
`Buy`). The tool skips `Sleep` listings by default because World66 deliberately
does not cover accommodation.

## Basic Workflow

```bash
python3 tools/wikivoyage_coverage.py download-dump
python3 tools/wikivoyage_coverage.py index-world66
python3 tools/wikivoyage_coverage.py import-wikivoyage tools/enwikivoyage-latest-pages-articles.xml.bz2
python3 tools/wikivoyage_coverage.py match-destinations
python3 tools/wikivoyage_coverage.py stats
```

The default database is:

```text
tools/wikivoyage_coverage.sqlite
```

## Reports

Show likely missing Wikivoyage listings for one destination:

```bash
python3 tools/wikivoyage_coverage.py missing --destination Paris
```

Write a CSV of missing listings for one destination:

```bash
python3 tools/wikivoyage_coverage.py missing --destination Paris --csv > paris_missing.csv
```

Summarize all matched destinations by apparent coverage:

```bash
python3 tools/wikivoyage_coverage.py destination-report
python3 tools/wikivoyage_coverage.py destination-report --csv > wikivoyage_coverage.csv
```

## Matching Rules

Destination pages are matched conservatively:

- exact normalized title, optionally confirmed by nearby coordinates
- fallback fuzzy title only when both pages have coordinates and are nearby

POIs/listings are considered covered when one of these is true:

- normalized names match exactly
- coordinates are within the configured radius, default `150m`
- normalized names are highly similar
- category and name similarity both line up

The output is a triage list. It should identify places to investigate, not
automatically create World66 pages.
