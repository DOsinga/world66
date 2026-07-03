# Score Examples

These files calibrate the four score dimensions from the model's 12 hidden travel dimensions.

Each dimension file has two lists:

- `positive`: places that should score high for that dimension.
- `negative`: places that should score low for that dimension.

Use location paths from `static/widgets/score-composer.json`, without a leading slash. Then rebuild the regression:

```bash
python3 tools/train_score_examples.py \
  --examples score_examples \
  --input static/widgets/score-composer.json \
  --model-out scoring/rubric_v4_full/example_score_regression.json \
  --widget-out static/widgets/score-composer.json \
  --alpha 25
```
