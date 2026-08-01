# Location Scoring Model

World66 location scoring has two layers:

1. A broad LLM-labeled training layer that teaches the neural model a travel-specific latent space.
2. A small human-steered anchor layer that turns the 12 latent dimensions into the public scores.

The model learns from destination identity captured by the embeddings for the name, parent chain, and lat/lng.

The current LLM-labeled run used four broad dimensions:

- `culture`: human meaning, history, art, architecture, food, street life, identity, and living traditions.
- `nature`: wildness, ecosystems, animals, plants, seascapes, landscapes, geology, and outdoor beauty.
- `leisure`: the finer things in life: comfort, beauty, pleasure, taste, style, service, shopping, fine dining, wellness, and resorts.
- `adventure`: edge and discovery: off-the-beaten-track routes, remote regions, hard logistics, uncertainty, perceived danger, and frontier feeling.

Those labels are useful for training the bottleneck model, but they are not the final public scoring language.

## Public Score Design

The public scoring layer should use five dimensions:

- `heritage`: historic depth, older built fabric, ruins, museums, monuments, architecture, and traditions that a traveler can actually experience.
- `vibrancy`: street life, food scenes, nightlife, markets, neighborhoods, contemporary creativity, density, energy, and surprise.
- `nature`: the non-human world as a reason to travel, especially wildlife, ecosystems, landforms, water, climate, scale, rarity, and natural beauty.
- `leisure`: cultivated pleasure: taste, beauty, style, indulgence, sensuality, service, shopping, fine dining, wellness, resorts, and ease.
- `adventure`: edge, discovery, commitment, nerve, uncertainty, difficult logistics, perceived danger, remoteness, unfamiliar systems, and physical challenge.

The old `culture` dimension should be split because it mixes two different travel pleasures. New York, Tokyo, Lagos, and Bangkok should be able to score very high for vibrancy without needing to look like Rome or Kyoto. Rome, Kyoto, Angkor, Samarkand, and Florence should be able to score very high for heritage without needing the same contemporary urban charge.

Do not keep `cultural significance` as a separate public factor. A place can be important to a culture or religion and still not be especially interesting to most travelers if that importance is not visible, accessible, vibrant, or historic in the visitor experience.

## Scoring Guidelines

Send this section to scoring agents verbatim. Do not paraphrase the dimensions in agent prompts.

Score each destination from `0` to `10` for `culture`, `nature`, `leisure`, and `adventure`.  Use only the destination name, parent chain, and coordinates from the batch. Score the ordinary visitor experience, not page quality, page text, POIs, or the most extreme optional activity nearby.

Scores mean:

- `0`: not a reason to visit this place.
- `5`: present and meaningful, but not exceptional.
- `10`: one of the world's strong examples of this dimension.

Keep the scores separate. The same destination can be high on several dimensions, but each high score needs its own reason.

### Culture

High culture scores mean strong human meaning. The score should reflect how deeply a place has been shaped by people, how much human story has accumulated there, and how vividly that story is still felt by visitors. The highest scores go to places with depth, distinctiveness, continuity, creativity, and a strong sense of human presence.

### Nature

High nature scores mean the living and physical natural world at its strongest. Wildlife, plants, ecosystems, landforms, water, ice, and climate shape the score, with animal life especially important when it defines the journey. The highest scores go to places that feel alive, wild, rare, vast, strange, or beautiful.

### Leisure

High leisure scores mean cultivated pleasure: taste, beauty, style, indulgence, sensuality, and being well looked after. The highest scores go to places where the ordinary visitor experience feels refined, glamorous, relaxing, delicious, restorative, or fun.

### Adventure

High adventure scores mean edge, discovery, and commitment. The score should reflect how much a trip asks from the visitor: nerve, effort, uncertainty, difficult logistics, perceived danger, unfamiliar systems, remoteness, or physical challenge. The highest scores go to places where the ordinary journey feels bold and story-worthy.

### Calibration Anchors

Use these anchors to keep the dimensions separate:

| Destination | Culture | Nature | Leisure | Adventure |
|---|---:|---:|---:|---:|
| Tokyo | 9 | 2 | 10 | 1 |
| Hawaii resort coast | 5 | 8 | 9 | 2 |
| Yellowstone standard visit | 4 | 9 | 5 | 2 |
| Serengeti safari | 3 | 9 | 6 | 4 |
| Bwindi gorilla trekking | 3 | 10 | 4 | 7 |
| Karakoram Highway | 6 | 9 | 2 | 10 |
| Lagos | 7 | 3 | 4 | 8 |
| Damascus | 9 | 2 | 1 | 9 |

## Pipeline

### 1. Sample locations

Eligible locations are exported from the filesystem content tree. The current training sample has 2000 locations.

```bash
python3 tools/scoring_dataset.py sample --n 2000 --seed 67 --out scoring/sample_1000.json
```

The filename is historical; `scoring/sample_1000.json` currently contains 2000 sampled locations.

### 2. Label locations

Create batches and ask agents to score them with the Scoring Guidelines above.

```bash
python3 tools/scoring_dataset.py batches \
  --sample scoring/rubric_v4_full/sample_2000.json \
  --size 50
```

The current v4 full run lives in:

- `scoring/rubric_v4_full/instructions.md`
- `scoring/rubric_v4_full/sample_2000.json`
- `scoring/rubric_v4_full/batches/`
- `scoring/rubric_v4_full/scores/`
- `scoring/rubric_v4_full/scored_2000.json`

### 3. Generate embeddings

Generate `text-embedding-3-large` embeddings for the labeled sample:

```bash
python3 tools/generate_scoring_embeddings.py \
  --sample scoring/sample_1000.json \
  --model text-embedding-3-large \
  --out scoring/location_embeddings_large.npz \
  --meta-out scoring/location_embeddings_large_meta.json
```

The generator uses `OPENAI_API_KEY` from the environment or from `.env`. Use `--env-file <path>` if needed.

### 4. Train the dimension model

Validate the current production architecture:

```bash
python3 tools/train_scoring_model.py \
  --embeddings scoring/location_embeddings_large.npz \
  --scores scoring/rubric_v4_full/scored_2000.json \
  --out-dir scoring/rubric_v4_full/models_validation \
  --weight-decay 0.1 \
  --dropout 0.2 \
  --only-config deep_128_32_hidden_12 \
  --epochs 400 \
  --patience 60
```

Current validation MAE:

| Culture | Nature | Leisure | Adventure |
|---:|---:|---:|---:|
| 0.96 | 1.11 | 0.89 | 0.88 |

Train the production model on all 2000 labels:

```bash
python3 tools/train_scoring_model.py \
  --embeddings scoring/location_embeddings_large.npz \
  --scores scoring/rubric_v4_full/scored_2000.json \
  --out-dir scoring/rubric_v4_full/production \
  --weight-decay 0.1 \
  --dropout 0.2 \
  --only-config deep_128_32_hidden_12 \
  --train-all \
  --final-epochs 250
```

### 5. Apply the model to all locations

Export all eligible locations, embed them, and predict dimensions:

```bash
python3 tools/scoring_dataset.py export-locations --out scoring/all_locations.json

python3 tools/generate_scoring_embeddings.py \
  --sample scoring/all_locations.json \
  --model text-embedding-3-large \
  --out scoring/all_location_embeddings_large.npz \
  --meta-out scoring/all_location_embeddings_large_meta.json

python3 tools/predict_location_dimensions.py \
  --embeddings scoring/all_location_embeddings_large.npz \
  --model scoring/rubric_v4_full/production/deep_128_32_hidden_12.pt \
  --out scoring/rubric_v4_full/all_location_dimensions.json \
  --hidden-out scoring/rubric_v4_full/all_location_hidden_12.npz
```

This currently predicts four travel dimensions for 7289 eligible locations.

Current all-location model correlations:

|  | Culture | Nature | Leisure | Adventure |
|---|---:|---:|---:|---:|
| Culture | 1.000 | -0.203 | 0.206 | -0.120 |
| Nature | -0.203 | 1.000 | 0.232 | 0.546 |
| Leisure | 0.206 | 0.232 | 1.000 | -0.459 |
| Adventure | -0.120 | 0.546 | -0.459 | 1.000 |

This is much better than the previous nature/adventure correlation of `0.765`, but the dimensions are still not independent enough for exact top-list ordering.

### 6. Calibrate dimensions with examples

The neural model produces 12 hidden travel dimensions. The current widget calibrates public scores from examples instead of hand-picked slider weights.

Put examples in:

- `score_examples/culture.json`
- `score_examples/nature.json`
- `score_examples/leisure.json`
- `score_examples/adventure.json`

Each file has `positive` and `negative` path lists. Positive examples train toward `10`; negative examples train toward `0`. Paths are the location paths used in `static/widgets/score-composer.json`.

Train the example regression and refresh the example-score widget:

```bash
python3 tools/train_score_examples.py \
  --examples score_examples \
  --input static/widgets/score-composer.json \
  --model-out scoring/rubric_v4_full/example_score_regression.json \
  --widget-out static/widgets/score-composer.json \
  --alpha 25
```

The script fits one ridge regression per public dimension from the 12 hidden values. It fails if an example path is not present in the widget data. The current default uses `alpha=25` to keep sparse examples from flattening too many destinations to `10`.

This positive/negative example format is useful for quick exploration. The production steering layer should move to scored anchors.

### 7. Score human steering anchors

Pick about 100 important travel places that are good steering opportunities. These should be famous places, edge cases, and places that separate dimensions cleanly. The goal is not a random sample; it is maximum steering value per human score.

Good anchors include:

- globally important cities: Paris, New York, Tokyo, London, Rome, Istanbul, Cairo, Bangkok.
- high-vibrancy cities: Lagos, Mexico City, Berlin, Mumbai, Seoul.
- high-heritage places: Kyoto, Florence, Angkor Wat, Samarkand, Varanasi, Teotihuacan.
- nature and wildlife anchors: Serengeti, Bwindi, Yellowstone, Galapagos, Torres del Paine.
- leisure anchors: Dubai, Miami, Cannes, Maldives, Las Vegas, Bora Bora.
- adventure anchors: Karakoram Highway, Djanet, Tenere Desert, Damascus, Everest Base Camp.
- confusing or failure-prone cases: Mecca, Big Sur, Denali, Hawaii resort coast, Venice, Singapore.

Seed each anchor with the model's current best guess, then let a human edit the values. The human should not start from a blank form.

The anchor file should look like:

```json
[
  {
    "path": "northamerica/unitedstates/newyorkstate/newyork",
    "name": "New York",
    "parent": "North America, United States, New York State",
    "scores": {
      "heritage": 8.0,
      "vibrancy": 10.0,
      "nature": 3.0,
      "leisure": 8.5,
      "adventure": 3.0
    }
  }
]
```

Train the final public scoring layer from:

```text
hidden_12 -> heritage, vibrancy, nature, leisure, adventure
```

Use a simple regularized regression first. The input has only 12 values, so 100 strong anchors should be enough to steer the model. If the top lists still look wrong, improve the anchor set before trying a more complex model.

### 8. Predict the old general score

To mimic the old `score` field, train a ridge regression over the four predicted dimensions plus the 12 hidden dimensions:

```bash
python3 tools/train_current_score_regression.py \
  --dimensions scoring/rubric_v4_full/all_location_dimensions.json \
  --hidden scoring/rubric_v4_full/all_location_hidden_12.npz \
  --model-out scoring/rubric_v4_full/current_score_regression_validation.json \
  --predictions-out scoring/rubric_v4_full/all_location_current_score_predictions_validation.json \
  --alpha 10.0

python3 tools/train_current_score_regression.py \
  --dimensions scoring/rubric_v4_full/all_location_dimensions.json \
  --hidden scoring/rubric_v4_full/all_location_hidden_12.npz \
  --model-out scoring/rubric_v4_full/current_score_regression.json \
  --predictions-out scoring/rubric_v4_full/all_location_current_score_predictions.json \
  --alpha 10.0 \
  --train-all
```

The v4-vector regression predicts the current score with about `0.57` validation MAE.

## Agent Runoffs

The neural network is good for broad coverage, but we should not expect it to order the top 50 or 100 places perfectly. For visible top lists, use agent runoffs as a ranking overlay.

The runoff process is:

1. Pick a recipe, such as `culture`, `nature`, `leisure`, `adventure`, `culture + leisure`, or a personalized vector.
2. Pull the top 50 to 100 candidates from the neural model. The current default is top 75.
3. Ask an agent to score only the target category or recipe, using the same Scoring Guidelines.
4. Store runoff scores separately from base model scores.
5. Use runoff ordering for visible top lists and recommendation surfaces. Fall back to the neural model below the runoff cutoff.

Runoffs are not a replacement for the base four scores. They are a hand-tuned ranking layer for the places where ordering matters most.
