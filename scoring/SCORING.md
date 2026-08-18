# Location Scoring Model

World66 location scoring has two main phases:

1. Ask LLMs to score sampled locations on four travel dimensions, using the text descriptions below.
2. Train a neural model that maps destination embeddings into a 12-dimensional travel space and predicts those four scores.
3. Build one production score from the four public scores with a weighted top-two recipe.

The model learns from destination identity captured by the embeddings for the name, parent chain, and lat/lng.

The current dimensions are `heritage`, `vibrancy`, `nature`, and `off_the_beaten_track`.

There are two sample sizes:

- `scoring/data/sampled.json` and `scoring/data/sampled_scored.json` contain 200 locations for rubric inspection and quick visual checks only. Do not train production models from this file.
- `scoring/data/sample_2000.json` and `scoring/data/scored_2000.json` are the training set for the latent model. When the rubric changes, rerun this 2000-location set before treating model output as production-quality.

## Scoring Guidelines

Send this section to scoring agents verbatim. Do not paraphrase the dimensions in agent prompts.

Score each destination from `0` to `10` for `heritage`, `vibrancy`, `nature`, and `off_the_beaten_track`. Use only the destination name, parent chain, and coordinates from the batch. Score the ordinary visitor experience, not page quality, page text, POIs, or the most extreme optional activity nearby. Use a global travel scale, not a scale relative to the other places in the batch.

Scores mean:

- `0`: not a reason to visit this place.
- `5`: present and meaningful, but not exceptional.
- `10`: one of the world's strong examples of this dimension.

Keep the scores separate. The same destination can be high on several dimensions, but each high score needs its own reason.

Use the calibration examples below to keep scores on a global scale, not relative to the other places in the batch. They are scale references, not extra locations to score.

### Heritage

High heritage scores mean visible historic depth, places that remind one of a past glory. The score should reflect old built fabric, ruins, monuments, museums, architecture, long traditions, and layered human memory that a traveler can actually experience.

Calibration examples:

- `10`: Rome, Kyoto, Angkor, Luxor.
- `7`: Boston, Istanbul's modern districts, Lisbon, Fez.
- `4`: Calgary, Brisbane, Cancun, modern resort towns with some older fabric.
- `1`: Las Vegas suburbs, airport towns, new beach developments.

### Vibrancy

High vibrancy scores mean urban electricity at a global travel scale: many-layered human activity, dense street life, strong food and night scenes, creative energy, distinctive neighborhoods, money, style, conversation, movement, and surprise. A 9 or 10 should feel like a complete urban world with depth across many scenes. Mid-high scores belong to memorable but narrower places: a great music city, party island, resort nightlife strip, regional food city, or city with one especially famous scene.

Calibration examples:

- `10`: Tokyo, New York, Bangkok, London, Paris.
- `7`: Budapest, Lisbon, Montreal, Taipei, strong regional cities with real energy and a few famous scenes.
- `4`: Bergen, Boise, smaller provincial cities with pleasant restaurants and some nightlife.
- `1`: quiet resort villages, commuter towns, remote service settlements.

### Nature

High nature scores mean the non-human world is a main reason to go. Score the strength of the natural payoff: animal life, green life, ecological richness, beauty, scale, and the feeling of being in a place shaped by forces larger than people. A destination can score very high when nature is vivid, abundant, beautiful, gentle, grand, or restorative, even when the visit is easy and well managed. Mountains, beaches and national parks.

Calibration examples:

- `10`: Serengeti, Galapagos, Great Barrier Reef, Torres del Paine.
- `7`: Amalfi Coast, Scottish Highlands, Lake District, Bali rice terraces.
- `4`: Paris parks, ordinary countryside, pleasant city beaches.
- `1`: dense urban cores with little natural appeal.

### Off The Beaten Track

High off-the-beaten-track scores mean the journey takes guts. Score what the trip asks from the traveler: nerve, effort, uncertainty, hard logistics, perceived danger, unfamiliar systems, physical challenge, commitment, and crossing into less managed territory. The score comes from the mode of travel and the edge of the experience, not from scenery alone. The highest scores go to places where a normal visit feels bold, exploratory, exposed, and story-worthy. Physical remoteness can matter, but it is not the only driver.

Calibration examples:

- `10`: Trans Sahara, rural Afghanistan, Danakil Depression, remote Papua highlands.
- `7`: trekking for gorillas in Bwindi, Pamir Highway, Socotra, Timbuktu.
- `4`: Marrakech, Naples, Guatemala highlands, lightly managed national parks.
- `1`: Tokyo, Paris, Singapore, Disney resort areas.

### Further instructions
Read these scoring rubrics and reflect on how they express different dimensions for a traveler. Heritage is not vibrancy. Nature is not off the beaten track.

## Files

Scoring is self-contained under `scoring/`:

```text
scoring/
  SCORING.md
  sample_locations.py
  score_batches.py
  generate_embeddings.py
  train_latent_model.py
  predict_locations.py
  seed_steering_candidates.py
  train_steering_layer.py
  build_location_scores.py
  apply_location_scores.py
  build_widget_data.py
  old_score_regression.py
```

Scripts live directly in `scoring/`. Generated files go in `scoring/data/`, but old runs should not be kept around once the scoring definitions change. After a complete four-score rerun, commit the finished artifacts needed to reproduce the current production scores.

## Pipeline

### 1. Sample locations

Eligible locations are exported from the filesystem content tree.

Use a 200-location sample only for rubric inspection and quick visual checks:

```bash
python3 scoring/sample_locations.py sample --n 200 --seed 71 --out scoring/data/sampled.json
```

`sampled.json`, `sampled.txt`, and `sampled_scored.json` are not training data. They exist so we can cheaply inspect whether the rubric and global calibration examples are producing sensible direct LLM labels.

Use a 2000-location sample for the latent model training run:

```bash
python3 scoring/sample_locations.py sample --n 2000 --seed 67 --out scoring/data/sample_2000.json
```

### 2. Label locations

Create batches from the 2000-location training sample and score them with the LLM Scoring Guidelines above. The prompt must include the full Scoring Guidelines section, including the global-scale calibration examples.

```bash
python3 scoring/sample_locations.py batches \
  --sample scoring/data/sample_2000.json \
  --size 50

python3 scoring/score_batches.py \
  --model gpt-5-mini
```

Training agent outputs are merged into:

```text
scoring/data/scored_2000.json
```

The raw batch files live in `scoring/data/batches/`; the scored batch files live in `scoring/data/agent_scores/`.

### 3. Generate embeddings

Export all eligible locations and generate `text-embedding-3-large` embeddings once. The training script filters this file down to labeled paths.

```bash
python3 scoring/sample_locations.py export-locations --out scoring/data/all_locations.json

python3 scoring/generate_embeddings.py \
  --sample scoring/data/all_locations.json \
  --model text-embedding-3-large \
  --out scoring/data/all_location_embeddings_large.npz \
  --meta-out scoring/data/all_location_embeddings_large_meta.json
```

The generator uses `OPENAI_API_KEY` from the environment or from `.env`. Use `--env-file <path>` if needed.

### 4. Train the latent model

Validate the current production architecture:

```bash
python3 scoring/train_latent_model.py \
  --embeddings scoring/data/all_location_embeddings_large.npz \
  --scores scoring/data/scored_2000.json \
  --out-dir scoring/data/models_validation \
  --weight-decay 0.1 \
  --dropout 0.2 \
  --only-config deep_128_32_hidden_12 \
  --epochs 400 \
  --patience 60
```

Record validation MAE in `scoring/data/latent_model_metrics.json` after each full rerun.

Train the production model on all 2000 labels:

```bash
python3 scoring/train_latent_model.py \
  --embeddings scoring/data/all_location_embeddings_large.npz \
  --scores scoring/data/scored_2000.json \
  --out-dir scoring/data \
  --weight-decay 0.1 \
  --dropout 0.2 \
  --only-config deep_128_32_hidden_12 \
  --train-all \
  --final-epochs 250
```

The production model is stored as `scoring/data/latent_model.pt`.

### 5. Apply the latent model to all locations

Predict the four LLM training labels plus the 12 hidden dimensions for all locations:

```bash
python3 scoring/predict_locations.py \
  --embeddings scoring/data/all_location_embeddings_large.npz \
  --model scoring/data/latent_model.pt \
  --out scoring/data/latent_label_scores.json \
  --hidden-out scoring/data/all_location_hidden_12.npz
```

`latent_label_scores.json` is the base score output. It is produced from the four text-described dimensions above.

### 6. Steer the final score head

The latent model is the broad travel feature extractor. For final visible rankings, freeze the model up to `all_location_hidden_12.npz` and train only the last mapping from those 12 latent values to the four public scores.

First seed editable text files from the current top candidates:

```bash
python3 scoring/seed_steering_candidates.py
```

This writes:

```text
scoring/data/steering/heritage_in.txt
scoring/data/steering/vibrancy_in.txt
scoring/data/steering/nature_in.txt
scoring/data/steering/off_the_beaten_track_in.txt
```

Each file contains the top 100 candidates for that public dimension. Each line starts with the destination path, followed by model score, model rank, name, and parent. Only the path is read by the trainer; the other columns are for humans.

For each dimension, copy the input file to an output file and edit the output file:

```text
scoring/data/steering/vibrancy_in.txt
scoring/data/steering/vibrancy_out.txt
```

Reorder rows to express the desired order and keep the 50 places that should define the visible top list. Delete rows that should not be in the reviewed top list. Add rows by path when an obvious destination is missing. Then train the final head:

```bash
python3 scoring/train_steering_layer.py
```

This writes:

```text
scoring/data/steering_layer.json
scoring/data/final_scores.json
```

The trainer keeps the new scores close to the base model globally, while giving stronger weight to the edited ordering. After prediction, it applies an explicit top-5 override for each dimension: the first five paths in each edited `_out.txt` file are stamped to deterministic top scores for that dimension. The learned steering head handles everything below that. Do not treat copied-but-unedited output files as an improvement; without human edits, the steering layer mostly preserves the current top lists.

### 7. Build production scores

`scoring/data/final_scores.json` contains the four steered component scores. Build the production five-field score artifact from it:

```bash
python3 scoring/build_location_scores.py
```

This writes:

```text
scoring/data/location_scores.json
scoring/data/score_recipe.json
```

`location_scores.json` is the canonical scoring artifact for downstream code. Each row is keyed by destination path and contains:

```json
{
  "score": 9.767,
  "heritage": 9.452,
  "vibrancy": 9.96,
  "nature": 3.919,
  "off_the_beaten_track": 1.316
}
```

The combined `score` is normalized to `0..10`. It is computed by first multiplying each component by its component preference weight, then taking the best two weighted components:

```text
weighted_component = component_score * component_weight
raw_score =
  top_component_weight * highest_weighted_component
+ second_component_weight * second_highest_weighted_component
score = raw_score / maximum_possible_raw_score * 10
```

Current production recipe:

```text
heritage              1.00
vibrancy              1.14
nature                1.02
off_the_beaten_track  0.72
top_component         3.70
second_component      1.60
```

These weights were fitted against a blind agent list of broadly important world tourist destinations. They express a general-purpose editorial ranking, not a truth about what every traveler should prefer.

### 8. Write scores to frontmatter

Write the production scores into the location markdown files:

```bash
python3 scoring/apply_location_scores.py
```

This syncs `score`, `heritage`, `vibrancy`, `nature`, and `off_the_beaten_track` from `scoring/data/location_scores.json` into the frontmatter for each matching `type: location` page.

The site reads these values from frontmatter. Do not make page rendering depend on reading the generated scoring JSON at request time.

Use a dry run to inspect the number of changed files before applying:

```bash
python3 scoring/apply_location_scores.py --dry-run
```

### 9. Sync scores into the search index

Refresh the scoring table in `search.db`:

```bash
python3 indexer.py --scores-only
```

This creates or refreshes `location_scores`, keyed by destination path. The table stores:

- the combined `score`
- the four public components
- the 12 hidden travel components used for similarity

The Django request path reads visible scores from markdown frontmatter and reads similar-place vectors from `search.db`. It should not load `scoring/data/location_scores.json` or `scoring/data/all_location_hidden_12.npz` at request time.

The normal indexer run also refreshes `location_scores`:

```bash
python3 indexer.py
```

Use `--scores-only` after score-only changes so we do not re-embed every content file just because score frontmatter changed.

### 10. Build widget data

Refresh the JSON used by the scoring widgets:

```bash
python3 scoring/build_widget_data.py
```

This writes:

- `static/widgets/scoring-explorer.json`
- `static/widgets/score-composer.json`

The scoring explorer uses `scoring/data/location_scores.json` when it exists. Otherwise it falls back to `scoring/data/latent_label_scores.json`. `static/widgets/score-composer.json` is only refreshed when `scoring/data/steering_layer.json` exists.

### 11. Old score diagnostic

`scoring/old_score_regression.py` fits the existing one-number `score` field from the four public component scores plus the 12 hidden dimensions. It writes the fitted model, the combined score predictions, and `scoring/data/old_location_scores.json`.

The old-score regression is a diagnostic only. It is no longer part of the production pipeline and should not be used to overwrite `scoring/data/location_scores.json`.

## Agent Runoffs

The neural network is good for broad coverage, but we should not expect it to order the top 50 or 100 places perfectly. For visible top lists, use agent runoffs as a ranking overlay.

The runoff process is:

1. Pick a recipe, such as `heritage`, `vibrancy`, `nature`, `off_the_beaten_track`, `heritage + vibrancy`, or a personalized vector.
2. Pull the top 50 to 100 candidates from the neural model. The current default is top 75.
3. Ask an agent to score only the target category or recipe, using the public score definitions above.
4. Store runoff scores separately from base model scores.
5. Use runoff ordering for visible top lists and recommendation surfaces. Fall back to the neural model below the runoff cutoff.

Runoffs are not implemented in the current artifacts. They are the next hand-tuned ranking layer for the places where ordering matters most.
