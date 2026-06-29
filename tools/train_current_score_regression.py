#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import frontmatter
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = PROJECT_DIR / "content"
SCORING_DIR = PROJECT_DIR / "scoring"
DIMENSIONS_FILE = SCORING_DIR / "all_location_dimensions.json"
HIDDEN_FILE = SCORING_DIR / "all_location_hidden_12.npz"
MODEL_OUT = SCORING_DIR / "current_score_regression.json"
PREDICTIONS_OUT = SCORING_DIR / "all_location_current_score_predictions.json"
DIMENSIONS = ("culture", "nature", "leisure", "adventure")


def md_path_for(content_path):
    directory_style = CONTENT_DIR / content_path / f"{Path(content_path).name}.md"
    if directory_style.exists():
        return directory_style
    return CONTENT_DIR / f"{content_path}.md"


def current_scores(paths):
    scores = {}
    for path in paths:
        md_path = md_path_for(path)
        if not md_path.exists():
            continue
        meta = frontmatter.load(md_path).metadata
        if meta.get("score") is None:
            continue
        try:
            scores[path] = float(meta["score"])
        except (TypeError, ValueError):
            continue
    return scores


def split_indices(n, seed, val_fraction):
    rng = np.random.default_rng(seed)
    indices = np.arange(n)
    rng.shuffle(indices)
    val_count = round(n * val_fraction)
    return indices[val_count:], indices[:val_count]


def standardize(x, train_idx):
    mean = x[train_idx].mean(axis=0, keepdims=True)
    std = x[train_idx].std(axis=0, keepdims=True)
    std[std < 1e-6] = 1.0
    return (x - mean) / std, mean, std


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
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    baseline = float(np.mean(np.abs(y - np.mean(y))))
    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "baseline_mae": round(baseline, 4)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dimensions", type=Path, default=DIMENSIONS_FILE)
    parser.add_argument("--hidden", type=Path, default=HIDDEN_FILE)
    parser.add_argument("--model-out", type=Path, default=MODEL_OUT)
    parser.add_argument("--predictions-out", type=Path, default=PREDICTIONS_OUT)
    parser.add_argument("--seed", type=int, default=66)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--alpha", type=float, default=10.0)
    parser.add_argument("--train-all", action="store_true")
    args = parser.parse_args()

    dimensions = json.loads(args.dimensions.read_text())
    hidden_data = np.load(args.hidden, allow_pickle=True)
    hidden_by_path = {path: row for path, row in zip(hidden_data["paths"].tolist(), hidden_data["hidden"])}
    paths = sorted(set(dimensions) & set(hidden_by_path))
    scores = current_scores(paths)
    trainable_paths = [path for path in paths if path in scores]

    x = np.array(
        [
            [dimensions[path][dimension] for dimension in DIMENSIONS] + hidden_by_path[path].tolist()
            for path in trainable_paths
        ],
        dtype=np.float64,
    )
    y = np.array([scores[path] for path in trainable_paths], dtype=np.float64)
    if args.train_all:
        train_idx = np.arange(len(trainable_paths))
        val_idx = np.array([], dtype=int)
    else:
        train_idx, val_idx = split_indices(len(trainable_paths), args.seed, args.val_fraction)
    x, mean, std = standardize(x, train_idx)
    coef = fit_ridge(x[train_idx], y[train_idx], args.alpha)

    train_metrics = metrics(predict(x[train_idx], coef), y[train_idx])
    val_metrics = None if args.train_all else metrics(predict(x[val_idx], coef), y[val_idx])

    all_x = np.array(
        [
            [dimensions[path][dimension] for dimension in DIMENSIONS] + hidden_by_path[path].tolist()
            for path in paths
        ],
        dtype=np.float64,
    )
    all_x = (all_x - mean) / std
    all_pred = np.clip(predict(all_x, coef), 1.0, 10.0)
    predictions = {path: round(float(value), 3) for path, value in zip(paths, all_pred)}

    args.model_out.write_text(
        json.dumps(
            {
                "alpha": args.alpha,
                "features": list(DIMENSIONS) + [f"hidden_{i}" for i in range(hidden_data["hidden"].shape[1])],
                "train_count": int(len(train_idx)),
                "val_count": int(len(val_idx)),
                "total_current_scores": len(trainable_paths),
                "train_metrics": train_metrics,
                "val_metrics": val_metrics,
                "coef": coef.tolist(),
                "mean": mean.ravel().tolist(),
                "std": std.ravel().tolist(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    args.predictions_out.write_text(json.dumps(predictions, indent=2, sort_keys=True) + "\n")
    print(f"train: {train_metrics}")
    print(f"val:   {val_metrics}")
    print(f"Wrote {len(predictions)} predictions to {args.predictions_out.resolve().relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
