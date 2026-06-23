# Wikivoyage POI Pilot

Pilot queue generated from filtered high-confidence Wikivoyage `see`/`do` coverage candidates.

Rules for workers:

- Treat candidate rows as leads, not content to copy.
- Add a POI only if it is clearly worth at least `score: 6.0` in the parent location.
- Verify it is not already covered under a nearby/alternate name.
- Verify coordinates before publishing; do not invent coordinates.
- Put POIs flat in `content/<world66_path>/<poi_slug>.md`.
- Use `type: poi`, `tags: [things_to_do, ...]`, `latitude`, `longitude`, `snippet`, `score`, and `sources`.
- Write original World66 prose: at least two useful paragraphs for real sights; do not copy Wikivoyage text.
- If rejecting a row, record why in the assigned `rejects_batch_NN.csv`.

Batches:

- `batch_01.csv`
- `batch_02.csv`
- `batch_03.csv`
- `batch_04.csv`
- `batch_05.csv`
