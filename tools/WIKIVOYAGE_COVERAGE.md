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

Show filtered candidate gaps for one destination:

```bash
python3 tools/wikivoyage_coverage.py candidates --destination Paris
```

Write a CSV of filtered candidate gaps for one destination:

```bash
python3 tools/wikivoyage_coverage.py candidates --destination Paris --csv > paris_candidates.csv
```

Sample candidate gaps across 100 destinations:

```bash
python3 tools/wikivoyage_coverage.py sample-candidates --limit 100 --csv > wikivoyage_candidate_sample.csv
```

Export a ranked queue for worker batches:

```bash
python3 tools/wikivoyage_coverage.py export-candidates \
  --limit 250 \
  --min-score 0.82 \
  --require-coords \
  --max-per-destination 2 \
  --exclude-csv todo/wikivoyage_poi_pilot/candidates_250.csv \
  --csv > wikivoyage_followup_250.csv
```

Show raw missing listings for debugging, including likely noise and aliases:

```bash
python3 tools/wikivoyage_coverage.py missing --destination Paris
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

## Candidate Filtering

The `candidates` and `sample-candidates` commands apply additional filters so
the output is more useful for content planning:

- suppress `go` transport listings by default
- suppress accommodation, embassies/consulates, tourist information offices,
  rentals, taxis, schools/classes, tour operators, clinics/hospitals, hotels,
  and similar operational rows
- suppress likely aliases where World66 already has a close name or coordinate
  match
- score rows higher when they have coordinates, external URLs, descriptions,
  strong travel terms, and high-value travel types such as `see` and `do`
- flag rows that need an external source, are far from the parent destination,
  lack coordinates, or look like weak travel candidates
- omit raw Wikivoyage descriptions from candidate CSV output by default

Use `--include-go`, `--include-noise`, or `--include-aliases` when auditing the
filters themselves.

Use `--include-descriptions` only for source-auditing. Worker queues should
avoid raw Wikivoyage prose so new POI copy stays original.
