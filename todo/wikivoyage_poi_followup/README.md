# Wikivoyage POI Follow-up Queue

This is a stricter follow-up queue generated after the first 250-row pilot.

Input filters:

- Wikivoyage `see` and `do` listings only.
- Candidate score `>= 0.82`.
- Coordinates required.
- Max 2 candidates per World66 destination before final sampling.
- Previous pilot candidates excluded via `todo/wikivoyage_poi_pilot/candidates_250.csv`.
- `far_from_parent` and `weak_travel_signal` candidates excluded.
- Raw Wikivoyage descriptions omitted from worker CSVs.

Worker rules:

- Treat candidate rows as leads, not source text.
- Add a POI only if it is clearly worth at least `score: 6.0` in the parent location.
- Verify it is not already covered under a nearby or alternate name.
- Verify coordinates and find at least one corroborating source beyond the Wikivoyage row when possible.
- Put POIs flat in `content/<world66_path>/<poi_slug>.md`.
- Use `type: poi`, `tags: [things_to_do, ...]`, `latitude`, `longitude`, `snippet`, `score`, and `sources`.
- Write original World66 prose with at least two useful paragraphs.
- If rejecting a row, record why in the assigned `rejects_batch_NN.csv`.

Batches:

- `batch_01.csv`
- `batch_02.csv`
- `batch_03.csv`
- `batch_04.csv`
- `batch_05.csv`
