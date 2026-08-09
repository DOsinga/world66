#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
STEERING_DIR = DATA_DIR / "steering"
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


def read_paths(path):
    paths = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(line.split("\t", 1)[0].strip())
    return paths


def load_dimension_lists(steering_dir, path_to_index):
    lists = {}
    missing = []
    for dimension in DIMENSIONS:
        in_file = steering_dir / f"{dimension}_in.txt"
        out_file = steering_dir / f"{dimension}_out.txt"
        if not in_file.exists():
            raise FileNotFoundError(f"Missing steering input file: {display_path(in_file)}")
        if not out_file.exists():
            missing.append(display_path(out_file))
            continue

        candidates = read_paths(in_file)
        desired = read_paths(out_file)
        for path in candidates + desired:
            if path not in path_to_index:
                raise ValueError(f"{path} is missing hidden values")
        if len(desired) != len(set(desired)):
            raise ValueError(f"{display_path(out_file)} contains duplicate paths")
        lists[dimension] = {
            "candidates": candidates,
            "desired": desired,
        }

    if missing:
        missing_list = "\n".join(f"- {path}" for path in missing)
        raise SystemExit(f"Create edited *_out.txt files before training:\n{missing_list}")
    return lists


def ranking_pairs(lists, path_to_index, target_top, max_pairs):
    pairs = []
    for dimension_index, dimension in enumerate(DIMENSIONS):
        candidates = lists[dimension]["candidates"]
        desired = lists[dimension]["desired"]
        desired_set = set(desired)
        omitted = [path for path in candidates if path not in desired_set]

        for left_index, left_path in enumerate(desired):
            for right_path in desired[left_index + 1 :]:
                pairs.append((dimension_index, path_to_index[left_path], path_to_index[right_path]))

        top_paths = desired[:target_top]
        for positive_path in top_paths:
            for negative_path in omitted:
                pairs.append((dimension_index, path_to_index[positive_path], path_to_index[negative_path]))

    if len(pairs) > max_pairs:
        rng = np.random.default_rng(71)
        keep = rng.choice(len(pairs), size=max_pairs, replace=False)
        pairs = [pairs[index] for index in keep]
    return torch.tensor(pairs, dtype=torch.long)


def metrics(pred, target):
    err = pred - target
    return {
        "mae": round(float(np.mean(np.abs(err))), 4),
        "rmse": round(float(np.sqrt(np.mean(err**2))), 4),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steering-dir", type=Path, default=STEERING_DIR)
    parser.add_argument("--hidden", type=Path, default=HIDDEN_FILE)
    parser.add_argument("--base-scores", type=Path, default=BASE_SCORES_FILE)
    parser.add_argument("--latent-model", type=Path, default=LATENT_MODEL_FILE)
    parser.add_argument("--model-out", type=Path, default=MODEL_OUT)
    parser.add_argument("--scores-out", type=Path, default=SCORES_OUT)
    parser.add_argument("--epochs", type=int, default=1500)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--distill-weight", type=float, default=0.08)
    parser.add_argument("--rank-weight", type=float, default=0.35)
    parser.add_argument("--rank-margin", type=float, default=0.2)
    parser.add_argument("--target-top", type=int, default=50)
    parser.add_argument("--max-pairs", type=int, default=50000)
    args = parser.parse_args()

    hidden_data = np.load(args.hidden, allow_pickle=True)
    paths = hidden_data["paths"].tolist()
    hidden = torch.tensor(hidden_data["hidden"].astype(np.float32))
    path_to_index = {path: index for index, path in enumerate(paths)}

    base_scores = load_json(args.base_scores)
    base_y = torch.tensor(score_matrix(base_scores, paths), dtype=torch.float32)
    lists = load_dimension_lists(args.steering_dir, path_to_index)
    pairs = ranking_pairs(lists, path_to_index, args.target_top, args.max_pairs)

    model = ScoreHead(hidden.shape[1], len(DIMENSIONS))
    init_from_latent_head(model, args.latent_model)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    for _ in range(args.epochs):
        optimizer.zero_grad()
        pred = model(hidden)
        loss = args.distill_weight * nn.functional.mse_loss(pred, base_y)
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
                "steering_dir": str(args.steering_dir),
                "pair_count": int(len(pairs)),
                "target_top": args.target_top,
                "distill_weight": args.distill_weight,
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
