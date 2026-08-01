#!/usr/bin/env python3

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from torch import nn

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCORING_DIR = PROJECT_DIR / "scoring"
DATA_DIR = SCORING_DIR / "data"
EMBEDDINGS_FILE = DATA_DIR / "location_embeddings_large.npz"
SCORED_FILE = DATA_DIR / "scored_2000.json"
MODEL_DIR = DATA_DIR / "models_validation"
DIMENSIONS = ("heritage", "vibrancy", "nature", "leisure", "adventure")


class DirectModel(nn.Module):
    def __init__(self, input_dim, output_dim):
        super().__init__()
        self.output = nn.Linear(input_dim, output_dim)

    def forward(self, x):
        return torch.sigmoid(self.output(x))


class BottleneckModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.hidden = nn.Linear(input_dim, hidden_dim)
        self.output = nn.Linear(hidden_dim, output_dim)

    def encode(self, x):
        return torch.tanh(self.hidden(x))

    def forward(self, x):
        return torch.sigmoid(self.output(self.encode(x)))


class RegularizedBottleneckModel(nn.Module):
    def __init__(self, input_dim, intermediate_dim, hidden_dim, output_dim, dropout):
        super().__init__()
        self.input = nn.Sequential(
            nn.Linear(input_dim, intermediate_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.hidden = nn.Linear(intermediate_dim, hidden_dim)
        self.output = nn.Linear(hidden_dim, output_dim)

    def encode(self, x):
        return torch.tanh(self.hidden(self.input(x)))

    def forward(self, x):
        return torch.sigmoid(self.output(self.encode(x)))


class DeepRegularizedBottleneckModel(nn.Module):
    def __init__(self, input_dim, intermediate_dim, second_dim, hidden_dim, output_dim, dropout):
        super().__init__()
        self.input = nn.Sequential(
            nn.Linear(input_dim, intermediate_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(intermediate_dim, second_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.hidden = nn.Linear(second_dim, hidden_dim)
        self.output = nn.Linear(hidden_dim, output_dim)

    def encode(self, x):
        return torch.tanh(self.hidden(self.input(x)))

    def forward(self, x):
        return torch.sigmoid(self.output(self.encode(x)))


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def score_dimensions(scores):
    first_scores = next(iter(scores.values()))
    if all(dimension in first_scores for dimension in DIMENSIONS):
        return DIMENSIONS
    return tuple(first_scores)


def load_data(embeddings_path, scores_path):
    embeddings = np.load(embeddings_path, allow_pickle=True)
    scores = json.loads(scores_path.read_text())
    dimensions = score_dimensions(scores)

    all_paths = embeddings["paths"].tolist()
    keep = [index for index, path in enumerate(all_paths) if path in scores]
    if not keep:
        raise SystemExit("no embedding paths have scores")

    paths = [all_paths[index] for index in keep]
    latitudes = embeddings["latitudes"].astype(np.float32)[:, None] / 90.0
    longitudes = embeddings["longitudes"].astype(np.float32)[:, None] / 180.0
    x_all = np.concatenate([embeddings["embeddings"].astype(np.float32), latitudes, longitudes], axis=1)
    x = x_all[keep]

    y = np.array(
        [[scores[path][dimension] / 10.0 for dimension in dimensions] for path in paths],
        dtype=np.float32,
    )
    return paths, x, y, dimensions


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
    return (x - mean) / std, mean.astype(np.float32), std.astype(np.float32)


def mae_by_dimension(pred, target, dimensions):
    err = torch.abs(pred - target).mean(dim=0).detach().cpu().numpy() * 10.0
    return {dimension: round(float(value), 3) for dimension, value in zip(dimensions, err)}


def train_one(model, x_train, y_train, x_val, y_val, dimensions, args):
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    loss_fn = nn.MSELoss()

    best_state = None
    best_val = float("inf")
    best_epoch = 0
    stale = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        optimizer.zero_grad()
        train_pred = model(x_train)
        train_loss = loss_fn(train_pred, y_train)
        train_loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_loss = loss_fn(model(x_val), y_val).item()

        if val_loss < best_val - 1e-7:
            best_val = val_loss
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= args.patience:
                break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        train_pred = model(x_train)
        val_pred = model(x_val)

    return {
        "best_epoch": best_epoch,
        "train_mse": round(float(loss_fn(train_pred, y_train).item()), 5),
        "val_mse": round(float(loss_fn(val_pred, y_val).item()), 5),
        "train_mae": mae_by_dimension(train_pred, y_train, dimensions),
        "val_mae": mae_by_dimension(val_pred, y_val, dimensions),
    }


def train_full(model, x_train, y_train, dimensions, args):
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    loss_fn = nn.MSELoss()

    for _ in range(args.final_epochs):
        model.train()
        optimizer.zero_grad()
        train_pred = model(x_train)
        train_loss = loss_fn(train_pred, y_train)
        train_loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        train_pred = model(x_train)

    return {
        "epochs": args.final_epochs,
        "train_mse": round(float(loss_fn(train_pred, y_train).item()), 5),
        "train_mae": mae_by_dimension(train_pred, y_train, dimensions),
    }


def model_configs():
    return [
        ("direct", "direct", None),
        ("hidden_12", "bottleneck", 12),
        ("hidden_24", "bottleneck", 24),
        ("intermediate_32_hidden_12", "regularized", (32, 12)),
        ("intermediate_64_hidden_12", "regularized", (64, 12)),
        ("intermediate_92_hidden_12", "regularized", (92, 12)),
        ("deep_92_32_hidden_12", "deep_regularized", (92, 32, 12)),
        ("deep_128_32_hidden_12", "deep_regularized", (128, 32, 12)),
    ]


def build_model(name, model_type, dims, input_dim, output_dim, dropout=0):
    if model_type == "direct":
        return DirectModel(input_dim, output_dim), None
    if model_type == "bottleneck":
        return BottleneckModel(input_dim, dims, output_dim), dims
    if model_type == "regularized":
        intermediate_dim, hidden_dim = dims
        return RegularizedBottleneckModel(input_dim, intermediate_dim, hidden_dim, output_dim, dropout), hidden_dim
    intermediate_dim, second_dim, hidden_dim = dims
    return DeepRegularizedBottleneckModel(input_dim, intermediate_dim, second_dim, hidden_dim, output_dim, dropout), hidden_dim


def save_model(path, model, name, model_type, dims, hidden_dim, dimensions, metrics, mean, std, train_idx, val_idx):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "model_name": name,
            "model_type": model_type,
            "model_dims": dims,
            "hidden_dim": hidden_dim,
            "dimensions": dimensions,
            "input_mean": mean,
            "input_std": std,
            "metrics": metrics,
            "train_idx": train_idx,
            "val_idx": val_idx,
        },
        path,
    )


def export_hidden_vectors(path, model, x_tensor, paths):
    if not hasattr(model, "encode"):
        return
    path = path.resolve()
    with torch.no_grad():
        hidden = model.encode(x_tensor).cpu().numpy().astype(np.float32)
    np.savez_compressed(path, paths=np.array(paths, dtype=object), hidden=hidden)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS_FILE)
    parser.add_argument("--scores", type=Path, default=SCORED_FILE)
    parser.add_argument("--out-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--seed", type=int, default=66)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--epochs", type=int, default=3000)
    parser.add_argument("--patience", type=int, default=250)
    parser.add_argument("--lr", type=float, default=0.003)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--only-config")
    parser.add_argument("--train-all", action="store_true")
    parser.add_argument("--final-epochs", type=int, default=250)
    args = parser.parse_args()

    set_seed(args.seed)
    paths, x, y, dimensions = load_data(args.embeddings, args.scores)
    if args.train_all:
        train_idx = np.arange(len(paths))
        val_idx = np.array([], dtype=int)
    else:
        train_idx, val_idx = split_indices(len(paths), args.seed, args.val_fraction)
    x, mean, std = standardize(x, train_idx)

    x_tensor = torch.tensor(x, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32)
    x_train, y_train = x_tensor[train_idx], y_tensor[train_idx]
    x_val, y_val = x_tensor[val_idx], y_tensor[val_idx]

    configs = model_configs()
    if args.only_config:
        configs = [config for config in configs if config[0] == args.only_config]
        if not configs:
            raise SystemExit(f"unknown config: {args.only_config}")

    all_metrics = {}
    for name, model_type, dims in configs:
        model, hidden_dim = build_model(name, model_type, dims, x.shape[1], output_dim=len(dimensions), dropout=args.dropout)

        if args.train_all:
            metrics = train_full(model, x_train, y_train, dimensions, args)
        else:
            metrics = train_one(model, x_train, y_train, x_val, y_val, dimensions, args)
        metrics["parameters"] = sum(p.numel() for p in model.parameters())
        metrics["hidden_dim"] = hidden_dim
        metrics["model_type"] = model_type
        all_metrics[name] = metrics

        model_path = args.out_dir / f"{name}.pt"
        hidden_path = args.out_dir / f"{name}_vectors.npz"
        if args.train_all and name == "deep_128_32_hidden_12":
            model_path = args.out_dir / "latent_model.pt"
            hidden_path = args.out_dir / "latent_model_hidden_12.npz"

        save_model(model_path, model, name, model_type, dims, hidden_dim, dimensions, metrics, mean, std, train_idx, val_idx)
        if name == "hidden_12":
            export_hidden_vectors(args.out_dir / "hidden_12_vectors.npz", model, x_tensor, paths)
        elif name == "intermediate_64_hidden_12":
            export_hidden_vectors(args.out_dir / "intermediate_64_hidden_12_vectors.npz", model, x_tensor, paths)
        elif name == "intermediate_92_hidden_12":
            export_hidden_vectors(args.out_dir / "intermediate_92_hidden_12_vectors.npz", model, x_tensor, paths)
        elif name == "deep_128_32_hidden_12":
            export_hidden_vectors(hidden_path, model, x_tensor, paths)

        if args.train_all:
            print(f"{name}: train_mse={metrics['train_mse']:.5f} train_mae={metrics['train_mae']}")
        else:
            print(f"{name}: val_mse={metrics['val_mse']:.5f} val_mae={metrics['val_mae']}")

    metrics_name = "latent_model_metrics.json" if args.train_all else "metrics.json"
    metrics_path = (args.out_dir / metrics_name).resolve()
    metrics_path.write_text(json.dumps(all_metrics, indent=2, sort_keys=True) + "\n")
    print(f"Wrote metrics to {metrics_path.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
