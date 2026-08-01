# Location Scoring Model

World66 location scoring has two main phases:

1. Ask LLMs to score sampled locations on five travel dimensions, using the text descriptions below.
2. Train a neural model that maps destination embeddings into a 12-dimensional travel space and predicts those five scores.

The model learns from destination identity captured by the embeddings for the name, parent chain, and lat/lng.

The current dimensions are `heritage`, `vibrancy`, `nature`, `leisure`, and `adventure`.

## Scoring Guidelines

Send this section to scoring agents verbatim. Do not paraphrase the dimensions in agent prompts.

Score each destination from `0` to `10` for `heritage`, `vibrancy`, `nature`, `leisure`, and `adventure`. Use only the destination name, parent chain, and coordinates from the batch. Score the ordinary visitor experience, not page quality, page text, POIs, or the most extreme optional activity nearby.

Scores mean:

- `0`: not a reason to visit this place.
- `5`: present and meaningful, but not exceptional.
- `10`: one of the world's strong examples of this dimension.

Keep the scores separate. The same destination can be high on several dimensions, but each high score needs its own reason.

### Heritage

High heritage scores mean visible historic depth. The score should reflect old built fabric, ruins, monuments, museums, architecture, long traditions, and layered human memory that a traveler can actually experience.

### Vibrancy

High vibrancy scores mean contemporary human energy. The score should reflect street life, food scenes, markets, nightlife, neighborhoods, creative life, density, movement, and surprise.

### Nature

High nature scores mean the living and physical natural world at its strongest. Wildlife, plants, ecosystems, landforms, water, ice, and climate shape the score, with animal life especially important when it defines the journey. The highest scores go to places that feel alive, wild, rare, vast, strange, or beautiful.

### Leisure

High leisure scores mean cultivated pleasure: taste, beauty, style, indulgence, sensuality, and being well looked after. The highest scores go to places where the ordinary visitor experience feels refined, glamorous, relaxing, delicious, restorative, or fun.

### Adventure

High adventure scores mean edge, discovery, and commitment. The score should reflect how much a trip asks from the visitor: nerve, effort, uncertainty, difficult logistics, perceived danger, unfamiliar systems, remoteness, or physical challenge. The highest scores go to places where the ordinary journey feels bold and story-worthy.

## Files

Scoring is self-contained under `scoring/`:

```text
scoring/
  SCORING.md
  sample_locations.py
  generate_embeddings.py
  train_latent_model.py
  predict_locations.py
  seed_anchors.py
  train_anchor_regression.py
  build_widget_data.py
  old_score_regression.py
```

Scripts live directly in `scoring/`. Generated files go in `scoring/data/`, but old runs should not be kept around once the scoring definitions change. After a complete five-score rerun, commit the finished artifacts needed to reproduce the current production scores.

## Pipeline

### 1. Sample locations

Eligible locations are exported from the filesystem content tree. The current training sample has 2000 locations.

```bash
python3 scoring/sample_locations.py sample --n 2000 --seed 67 --out scoring/data/sample_2000.json
```

### 2. Label locations

Create batches and ask agents to score them with the LLM Scoring Guidelines above.

```bash
python3 scoring/sample_locations.py batches \
  --sample scoring/data/sample_2000.json \
  --size 50
```

Agent outputs are merged into:

```text
scoring/data/scored_2000.json
```

The raw batch files live in `scoring/data/batches/`; the scored batch files live in `scoring/data/scores/`.

### 3. Generate embeddings

Generate `text-embedding-3-large` embeddings for the labeled sample:

```bash
python3 scoring/generate_embeddings.py \
  --sample scoring/data/sample_2000.json \
  --model text-embedding-3-large \
  --out scoring/data/location_embeddings_large.npz \
  --meta-out scoring/data/location_embeddings_large_meta.json
```

The generator uses `OPENAI_API_KEY` from the environment or from `.env`. Use `--env-file <path>` if needed.

### 4. Train the latent model

Validate the current production architecture:

```bash
python3 scoring/train_latent_model.py \
  --embeddings scoring/data/location_embeddings_large.npz \
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
  --embeddings scoring/data/location_embeddings_large.npz \
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

Export all eligible locations for embedding, embed them, and predict the five LLM training labels plus the 12 hidden dimensions:

```bash
python3 scoring/sample_locations.py export-locations --out scoring/data/all_locations.json

python3 scoring/generate_embeddings.py \
  --sample scoring/data/all_locations.json \
  --model text-embedding-3-large \
  --out scoring/data/all_location_embeddings_large.npz \
  --meta-out scoring/data/all_location_embeddings_large_meta.json

python3 scoring/predict_locations.py \
  --embeddings scoring/data/all_location_embeddings_large.npz \
  --model scoring/data/latent_model.pt \
  --out scoring/data/latent_label_scores.json \
  --hidden-out scoring/data/all_location_hidden_12.npz
```

`latent_label_scores.json` is the current score output. It is produced from the five text-described dimensions above.

### 6. Build widget data

Refresh the JSON used by the scoring widgets:

```bash
python3 scoring/build_widget_data.py
```

This writes:

- `static/widgets/scoring-explorer.json`

`static/widgets/score-composer.json` is only refreshed when a later steering regression exists.

### 7. Old score diagnostic

`scoring/old_score_regression.py` is a diagnostic, not the public scoring path. It checks how well the latent labels and hidden dimensions can mimic the existing one-number `score` field.

The old v4-vector regression predicted the current score with about `0.57` validation MAE.

## Later Human Steering

After the first full five-score run, we can create a steering file from the model's initial scores for a small set of important destinations. Humans can then edit those scores directly and train a small regression from `hidden_12` to the human-edited five scores.

That steering file should be created from the current model output when we are ready to tune it. It should not exist before the first five-score run, and it should not be mixed with the scoring instructions above.

The helper scripts for that one-off pass are:

```bash
python3 scoring/seed_anchors.py
python3 scoring/train_anchor_regression.py
```

## Agent Runoffs

The neural network is good for broad coverage, but we should not expect it to order the top 50 or 100 places perfectly. For visible top lists, use agent runoffs as a ranking overlay.

The runoff process is:

1. Pick a recipe, such as `heritage`, `vibrancy`, `nature`, `leisure`, `adventure`, `heritage + leisure`, or a personalized vector.
2. Pull the top 50 to 100 candidates from the neural model. The current default is top 75.
3. Ask an agent to score only the target category or recipe, using the public score definitions above.
4. Store runoff scores separately from base model scores.
5. Use runoff ordering for visible top lists and recommendation surfaces. Fall back to the neural model below the runoff cutoff.

Runoffs are not implemented in the current artifacts. They are the next hand-tuned ranking layer for the places where ordering matters most.
