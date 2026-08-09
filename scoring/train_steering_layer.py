#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
STEERING_FILE = DATA_DIR / "steering_scores.json"
HIDDEN_FILE = DATA_DIR / "all_location_hidden_12.npz"
BASE_SCORES_FILE = DATA_DIR / "latent_label_scores.json"
LATENT_MODEL_FILE = DATA_DIR / "latent_model.pt"
MODEL_OUT = DATA_DIR / "steering_layer.json"
SCORES_OUT = DATA_DIR / "final_scores.json"
DIMENSIONS = ("heritage", "vibrancy", "nature", "off_the_beaten_track")


class ScoreHead(nn.Module):
    def __init__(self, input_dim, output_dim):
        super().__init__()
        self.output = nn.Linear(input_dim, output_dim)

    def forward(self, x):
        return torch.sigmoid(self.output(x)) * 10.0


def load_json(path):
    return json.loads(path.read_text())


def display_path(path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_DIR)
    except ValueError:
        return resolved


def score_matrix(scores, paths):
    return np.array(
        [[scores[path][dimension] for dimension in DIMENSIONS] for path in paths],
        dtype=np.float32,
    )


def init_from_latent_head(model, latent_model_path):
    checkpoint = torch.load(latent_model_path, weights_only=False)
    state = checkpoint["model_state"]
    model.output.weight.data.copy_(state["output.weight"])
    model.output.bias.data.copy_(state["output.bias"])


def load_steering(path, path_to_index):
    rows = load_json(path)
    seen = set()
    for row in rows:
        row_path = row["path"]
        if row_path in seen:
            raise ValueError(f"Duplicate steering row: {row_path}")
        if row_path not in path_to_index:
            raise ValueError(f"Steering row is missing hidden values: {row_path}")
        seen.add(row_path)
    return rows


def target_score_tensors(rows, path_to_index):
    indices = []
    targets = []
    mask = []
    for row in rows:
        row_targets = []
        row_mask = []
        for dimension in DIMENSIONS:
            value = row.get("target_scores", {}).get(dimension)
            row_targets.append(0.0 if value is None else float(value))
            row_mask.append(value is not None)
        if any(row_mask):
            indices.append(path_to_index[row["path"]])
            targets.append(row_targets)
            mask.append(row_mask)
    return (
        torch.tensor(indices, dtype=torch.long),
        torch.tensor(targets, dtype=torch.float32),
        torch.tensor(mask, dtype=torch.bool),
    )


def ranking_pairs(rows, path_to_index, max_pairs):
    pairs = []
    for dimension_index, dimension in enumerate(DIMENSIONS):
        positives = []
        negatives = []
        for row in rows:
            target = row.get("target_top_50", {}).get(dimension)
            if target is True:
                positives.append(path_to_index[row["path"]])
            elif target is False:
                negatives.append(path_to_index[row["path"]])
        for positive in positives:
            for negative in negatives:
                pairs.append((dimension_index, positive, negative))

    if len(pairs) > max_pairs:
        rng = np.random.default_rng(71)
        keep = rng.choice(len(pairs), size=max_pairs, replace=False)
        pairs = [pairs[index] for index in keep]
    return torch.tensor(pairs, dtype=torch.long)


def masked_mse(pred, target, mask):
    diff = pred - target
    return ((diff[mask]) ** 2).mean()


def metrics(pred, target):
    err = pred - target
    return {
        "mae": round(float(np.mean(np.abs(err))), 4),
        "rmse": round(float(np.sqrt(np.mean(err**2))), 4),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steering", type=Path, default=STEERING_FILE)
    parser.add_argument("--hidden", type=Path, default=HIDDEN_FILE)
    parser.add_argument("--base-scores", type=Path, default=BASE_SCORES_FILE)
    parser.add_argument("--latent-model", type=Path, default=LATENT_MODEL_FILE)
    parser.add_argument("--model-out", type=Path, default=MODEL_OUT)
    parser.add_argument("--scores-out", type=Path, default=SCORES_OUT)
    parser.add_argument("--epochs", type=int, default=1500)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--distill-weight", type=float, default=0.08)
    parser.add_argument("--score-weight", type=float, default=1.0)
    parser.add_argument("--rank-weight", type=float, default=0.35)
    parser.add_argument("--rank-margin", type=float, default=0.2)
    parser.add_argument("--max-pairs", type=int, default=50000)
    args = parser.parse_args()

    hidden_data = np.load(args.hidden, allow_pickle=True)
    paths = hidden_data["paths"].tolist()
    hidden = torch.tensor(hidden_data["hidden"].astype(np.float32))
    path_to_index = {path: index for index, path in enumerate(paths)}

    base_scores = load_json(args.base_scores)
    base_y = torch.tensor(score_matrix(base_scores, paths), dtype=torch.float32)
    rows = load_steering(args.steering, path_to_index)
    target_indices, target_y, target_mask = target_score_tensors(rows, path_to_index)
    pairs = ranking_pairs(rows, path_to_index, args.max_pairs)

    model = ScoreHead(hidden.shape[1], len(DIMENSIONS))
    init_from_latent_head(model, args.latent_model)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    for _ in range(args.epochs):
        optimizer.zero_grad()
        pred = model(hidden)
        loss = args.distill_weight * nn.functional.mse_loss(pred, base_y)
        if len(target_indices):
            target_pred = pred[target_indices]
            loss = loss + args.score_weight * masked_mse(target_pred, target_y, target_mask)
        if len(pairs):
            dim = pairs[:, 0]
            positive = pred[pairs[:, 1], dim]
            negative = pred[pairs[:, 2], dim]
            loss = loss + args.rank_weight * nn.functional.softplus(negative - positive + args.rank_margin).mean()
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        pred = model(hidden).numpy()

    output_scores = {
        path: {
            dimension: round(float(value), 3)
            for dimension, value in zip(DIMENSIONS, row)
        }
        for path, row in zip(paths, pred)
    }

    base_np = base_y.numpy()
    args.model_out.write_text(
        json.dumps(
            {
                "dimensions": list(DIMENSIONS),
                "features": [f"hidden_{index}" for index in range(hidden.shape[1])],
                "steering_count": len(rows),
                "pair_count": int(len(pairs)),
                "distill_weight": args.distill_weight,
                "score_weight": args.score_weight,
                "rank_weight": args.rank_weight,
                "rank_margin": args.rank_margin,
                "base_vs_final": metrics(pred, base_np),
                "weight": model.output.weight.detach().numpy().tolist(),
                "bias": model.output.bias.detach().numpy().tolist(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    args.scores_out.write_text(json.dumps(output_scores, indent=2, sort_keys=True) + "\n")
    print(f"base vs final: {metrics(pred, base_np)}")
    print(f"Wrote {len(output_scores)} final scores to {display_path(args.scores_out)}")


if __name__ == "__main__":
    main()
