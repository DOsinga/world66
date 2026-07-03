#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
DIMENSIONS = ("culture", "nature", "leisure", "adventure")
DEFAULT_EXAMPLES = PROJECT_DIR / "score_examples"
DEFAULT_INPUT = PROJECT_DIR / "static" / "widgets" / "score-composer.json"
DEFAULT_MODEL_OUT = PROJECT_DIR / "scoring" / "rubric_v4_full" / "example_score_regression.json"
DEFAULT_WIDGET_OUT = PROJECT_DIR / "static" / "widgets" / "score-composer.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def project_path(path):
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_DIR))
    except ValueError:
        return str(resolved)


def fit_ridge(x, y, alpha):
    x_aug = np.concatenate([np.ones((x.shape[0], 1)), x], axis=1)
    penalty = np.eye(x_aug.shape[1]) * alpha
    penalty[0, 0] = 0
    return np.linalg.solve(x_aug.T @ x_aug + penalty, x_aug.T @ y)


def predict(x, coef):
    x_aug = np.concatenate([np.ones((x.shape[0], 1)), x], axis=1)
    return x_aug @ coef


def metrics(pred, y):
    err = pred - y
    return {
        "mae": round(float(np.mean(np.abs(err))), 4),
        "rmse": round(float(np.sqrt(np.mean(err**2))), 4),
        "min": round(float(np.min(pred)), 4),
        "max": round(float(np.max(pred)), 4),
    }


def examples_for_dimension(examples_dir, dimension, location_by_path):
    data = load_json(examples_dir / f"{dimension}.json")
    rows = []
    seen = set()
    for label, target in (("positive", 10.0), ("negative", 0.0)):
        for path in data.get(label, []):
            if path in seen:
                raise ValueError(f"{path} appears more than once in {dimension}.json")
            if path not in location_by_path:
                raise ValueError(f"{path} from {dimension}.json is not in the score-composer data")
            seen.add(path)
            rows.append((path, target))
    if len(rows) < 2:
        raise ValueError(f"{dimension}.json needs at least one positive and one negative example")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples", type=Path, default=DEFAULT_EXAMPLES)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL_OUT)
    parser.add_argument("--widget-out", type=Path, default=DEFAULT_WIDGET_OUT)
    parser.add_argument("--alpha", type=float, default=25.0)
    args = parser.parse_args()

    widget_data = load_json(args.input)
    locations = widget_data["locations"]
    location_by_path = {location["path"]: location for location in locations}
    hidden_dim = len(locations[0]["hidden"])

    models = {}
    defaults = {}
    reports = {}
    all_hidden = np.array([location["hidden"] for location in locations], dtype=np.float64)

    for dimension in DIMENSIONS:
        examples = examples_for_dimension(args.examples, dimension, location_by_path)
        x = np.array([location_by_path[path]["hidden"] for path, _ in examples], dtype=np.float64)
        y = np.array([target for _, target in examples], dtype=np.float64)
        coef = fit_ridge(x, y, args.alpha)
        example_pred = np.clip(predict(x, coef), 0.0, 10.0)
        all_pred = np.clip(predict(all_hidden, coef), 0.0, 10.0)

        defaults[dimension] = {
            "bias": round(float(coef[0]), 6),
            "weights": [round(float(value), 6) for value in coef[1:]],
            "activation": "linear_clamped",
        }
        models[dimension] = {
            "positive": [path for path, target in examples if target == 10.0],
            "negative": [path for path, target in examples if target == 0.0],
            "coef": [float(value) for value in coef],
            "metrics": metrics(example_pred, y),
            "prediction_range": {
                "min": round(float(np.min(all_pred)), 4),
                "max": round(float(np.max(all_pred)), 4),
            },
        }
        reports[dimension] = models[dimension]["metrics"]

    widget_data["source"] = "score_examples/*.json + static/widgets/score-composer.json hidden vectors"
    widget_data["defaults"] = defaults
    widget_data["exampleModel"] = {
        "alpha": args.alpha,
        "hidden_dim": hidden_dim,
        "model": project_path(args.model_out),
    }

    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    args.model_out.write_text(
        json.dumps(
            {
                "alpha": args.alpha,
                "features": [f"hidden_{i}" for i in range(hidden_dim)],
                "dimensions": models,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    args.widget_out.write_text(json.dumps(widget_data, separators=(",", ":")) + "\n", encoding="utf-8")

    print(json.dumps(reports, indent=2, sort_keys=True))
    print(f"Wrote {project_path(args.model_out)}")
    print(f"Wrote {project_path(args.widget_out)}")


if __name__ == "__main__":
    main()
