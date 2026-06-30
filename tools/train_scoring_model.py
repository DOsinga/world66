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
EMBEDDINGS_FILE = SCORING_DIR / "location_embeddings.npz"
SCORED_FILE = SCORING_DIR / "scored.json"
MODEL_DIR = SCORING_DIR / "models"
DIMENSIONS = ("culture", "nature", "leisure", "adventure")


class DirectModel(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.output = nn.Linear(input_dim, len(DIMENSIONS))

    def forward(self, x):
        return torch.sigmoid(self.output(x))


class BottleneckModel(nn.Module):
    def __init__(self, input_dim, hidden_dim):
        super().__init__()
        self.hidden = nn.Linear(input_dim, hidden_dim)
        self.output = nn.Linear(hidden_dim, len(DIMENSIONS))

    def encode(self, x):
        return torch.tanh(self.hidden(x))

    def forward(self, x):
        return torch.sigmoid(self.output(self.encode(x)))


class RegularizedBottleneckModel(nn.Module):
    def __init__(self, input_dim, intermediate_dim, hidden_dim, dropout):
        super().__init__()
        self.input = nn.Sequential(
            nn.Linear(input_dim, intermediate_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.hidden = nn.Linear(intermediate_dim, hidden_dim)
        self.output = nn.Linear(hidden_dim, len(DIMENSIONS))

    def encode(self, x):
        return torch.tanh(self.hidden(self.input(x)))

    def forward(self, x):
        return torch.sigmoid(self.output(self.encode(x)))


class DeepRegularizedBottleneckModel(nn.Module):
    def __init__(self, input_dim, intermediate_dim, second_dim, hidden_dim, dropout):
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
        self.output = nn.Linear(hidden_dim, len(DIMENSIONS))

    def encode(self, x):
        return torch.tanh(self.hidden(self.input(x)))

    def forward(self, x):
        return torch.sigmoid(self.output(self.encode(x)))


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_data(embeddings_path, scores_path):
    embeddings = np.load(embeddings_path, allow_pickle=True)
    scores = json.loads(scores_path.read_text())

    paths = embeddings["paths"].tolist()
    latitudes = embeddings["latitudes"].astype(np.float32)[:, None] / 90.0
    longitudes = embeddings["longitudes"].astype(np.float32)[:, None] / 180.0
    x = np.concatenate([embeddings["embeddings"].astype(np.float32), latitudes, longitudes], axis=1)

    missing = [path for path in paths if path not in scores]
    if missing:
        raise SystemExit(f"missing scores for {len(missing)} paths, first: {missing[0]}")

    y = np.array(
        [[scores[path][dimension] / 10.0 for dimension in DIMENSIONS] for path in paths],
        dtype=np.float32,
    )
    return paths, x, y


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


def mae_by_dimension(pred, target):
    err = torch.abs(pred - target).mean(dim=0).detach().cpu().numpy() * 10.0
    return {dimension: round(float(value), 3) for dimension, value in zip(DIMENSIONS, err)}


def train_one(model, x_train, y_train, x_val, y_val, args):
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
        "train_mae": mae_by_dimension(train_pred, y_train),
        "val_mae": mae_by_dimension(val_pred, y_val),
    }


def train_full(model, x_train, y_train, args):
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
        "train_mae": mae_by_dimension(train_pred, y_train),
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


def build_model(name, model_type, dims, input_dim, dropout):
    if model_type == "direct":
        return DirectModel(input_dim), None
    if model_type == "bottleneck":
        return BottleneckModel(input_dim, dims), dims
    if model_type == "regularized":
        intermediate_dim, hidden_dim = dims
        return RegularizedBottleneckModel(input_dim, intermediate_dim, hidden_dim, dropout), hidden_dim
    intermediate_dim, second_dim, hidden_dim = dims
    return DeepRegularizedBottleneckModel(input_dim, intermediate_dim, second_dim, hidden_dim, dropout), hidden_dim


def save_model(path, model, name, model_type, dims, hidden_dim, metrics, mean, std, train_idx, val_idx):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "model_name": name,
            "model_type": model_type,
            "model_dims": dims,
            "hidden_dim": hidden_dim,
            "dimensions": DIMENSIONS,
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
    paths, x, y = load_data(args.embeddings, args.scores)
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
        model, hidden_dim = build_model(name, model_type, dims, x.shape[1], args.dropout)

        if args.train_all:
            metrics = train_full(model, x_train, y_train, args)
        else:
            metrics = train_one(model, x_train, y_train, x_val, y_val, args)
        metrics["parameters"] = sum(p.numel() for p in model.parameters())
        metrics["hidden_dim"] = hidden_dim
        metrics["model_type"] = model_type
        all_metrics[name] = metrics

        save_model(args.out_dir / f"{name}.pt", model, name, model_type, dims, hidden_dim, metrics, mean, std, train_idx, val_idx)
        if name == "hidden_12":
            export_hidden_vectors(args.out_dir / "hidden_12_vectors.npz", model, x_tensor, paths)
        elif name == "intermediate_64_hidden_12":
            export_hidden_vectors(args.out_dir / "intermediate_64_hidden_12_vectors.npz", model, x_tensor, paths)
        elif name == "intermediate_92_hidden_12":
            export_hidden_vectors(args.out_dir / "intermediate_92_hidden_12_vectors.npz", model, x_tensor, paths)
        elif name == "deep_128_32_hidden_12":
            export_hidden_vectors(args.out_dir / "deep_128_32_hidden_12_vectors.npz", model, x_tensor, paths)

        if args.train_all:
            print(f"{name}: train_mse={metrics['train_mse']:.5f} train_mae={metrics['train_mae']}")
        else:
            print(f"{name}: val_mse={metrics['val_mse']:.5f} val_mae={metrics['val_mae']}")

    metrics_path = (args.out_dir / "metrics.json").resolve()
    metrics_path.write_text(json.dumps(all_metrics, indent=2, sort_keys=True) + "\n")
    print(f"Wrote metrics to {metrics_path.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
