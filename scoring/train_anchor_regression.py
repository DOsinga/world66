#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
ANCHORS_FILE = DATA_DIR / "anchors.json"
HIDDEN_FILE = DATA_DIR / "all_location_hidden_12.npz"
MODEL_OUT = DATA_DIR / "anchor_score_regression.json"
SCORES_OUT = DATA_DIR / "location_scores.json"
DIMENSIONS = ("heritage", "vibrancy", "nature", "leisure", "adventure")


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
    }


def load_anchors(path, hidden_by_path):
    anchors = json.loads(path.read_text())
    rows = []
    seen = set()
    for anchor in anchors:
        anchor_path = anchor["path"]
        if anchor_path in seen:
            raise ValueError(f"Duplicate anchor: {anchor_path}")
        if anchor_path not in hidden_by_path:
            raise ValueError(f"Anchor is missing hidden values: {anchor_path}")
        scores = anchor["scores"]
        missing = [dimension for dimension in DIMENSIONS if dimension not in scores]
        if missing:
            raise ValueError(f"{anchor_path} is missing scores for {', '.join(missing)}")
        seen.add(anchor_path)
        rows.append(anchor)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchors", type=Path, default=ANCHORS_FILE)
    parser.add_argument("--hidden", type=Path, default=HIDDEN_FILE)
    parser.add_argument("--model-out", type=Path, default=MODEL_OUT)
    parser.add_argument("--scores-out", type=Path, default=SCORES_OUT)
    parser.add_argument("--alpha", type=float, default=25.0)
    args = parser.parse_args()

    hidden_data = np.load(args.hidden, allow_pickle=True)
    paths = hidden_data["paths"].tolist()
    hidden = hidden_data["hidden"].astype(np.float64)
    hidden_by_path = {path: row for path, row in zip(paths, hidden)}
    anchors = load_anchors(args.anchors, hidden_by_path)

    x = np.array([hidden_by_path[anchor["path"]] for anchor in anchors], dtype=np.float64)
    y = np.array([[anchor["scores"][dimension] for dimension in DIMENSIONS] for anchor in anchors], dtype=np.float64)
    coef = fit_ridge(x, y, args.alpha)

    anchor_pred = np.clip(predict(x, coef), 0.0, 10.0)
    all_pred = np.clip(predict(hidden, coef), 0.0, 10.0)
    output_scores = {
        path: {
            dimension: round(float(value), 3)
            for dimension, value in zip(DIMENSIONS, row)
        }
        for path, row in zip(paths, all_pred)
    }

    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    args.model_out.write_text(
        json.dumps(
            {
                "alpha": args.alpha,
                "dimensions": list(DIMENSIONS),
                "features": [f"hidden_{i}" for i in range(hidden.shape[1])],
                "anchor_count": len(anchors),
                "metrics": metrics(anchor_pred, y),
                "coef": coef.tolist(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    args.scores_out.write_text(json.dumps(output_scores, indent=2, sort_keys=True) + "\n")
    print(f"train: {metrics(anchor_pred, y)}")
    print(f"Wrote {len(output_scores)} scores to {args.scores_out.resolve().relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
