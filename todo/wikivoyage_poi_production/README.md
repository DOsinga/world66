# Wikivoyage POI Production Queue

This queue is for processing the top 30,000 Wikivoyage `see` and `do` candidate gaps, not for benchmarking.

Generation command:

```bash
python3 tools/wikivoyage_coverage.py export-candidates \
  --db /tmp/wikivoyage_coverage_filtered.sqlite \
  --limit 30000 \
  --min-score 0 \
  --max-per-destination 0 \
  --exclude-flags weak_travel_signal \
  --listing-types see,do \
  --exclude-csv todo/wikivoyage_poi_pilot/candidates_250.csv \
  --csv > /tmp/wikivoyage_production_30000.csv
```

Queue shape:

- 30,000 candidate rows.
- 600 batches of 50 rows in `batches/`.
- 20,407 `see` candidates.
- 9,593 `do` candidates.
- 3,528 unique World66 destinations.
- Previous 250 pilot candidates are excluded.
- Raw Wikivoyage descriptions are omitted from worker CSVs.

Important flags:

- `needs_external_source`: Wikivoyage did not provide an external URL; workers must find corroboration before adding.
- `missing_coordinates`: Wikivoyage did not provide lat/lng; workers must find and verify coordinates before adding.
- `far_from_parent`: candidate may be a day trip, separate feature, or wrongly attached listing.
- `day_trip_review`: candidate is meaningfully away from the parent but not extreme.

Worker rules:

- Treat rows as leads only.
- Add a POI only if it clears `score: 6.0` for the parent location.
- Verify duplicates and aliases before adding.
- Verify coordinates; do not invent them.
- Add at least one corroborating source beyond Wikivoyage when possible, especially for rows flagged `needs_external_source`.
- Put POIs flat in `content/<world66_path>/<poi_slug>.md`.
- Use `type: poi`, `tags: [things_to_do, ...]`, `latitude`, `longitude`, `snippet`, `score`, and `sources`.
- Write original World66 prose with at least two useful paragraphs.
- Record rejected rows in `rejects_batch_NNNN.csv` next to the processed batch or in a worker summary.

Processing suggestion:

Assign batches by filename range, for example `batch_0001.csv` through `batch_0050.csv`, so workers can run independently and avoid merge churn.
