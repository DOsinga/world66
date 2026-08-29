#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from train_latent_model import build_model

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCORING_DIR = PROJECT_DIR / "scoring"
DATA_DIR = SCORING_DIR / "data"
EMBEDDINGS_FILE = DATA_DIR / "all_location_embeddings_large.npz"
MODEL_FILE = DATA_DIR / "latent_model.pt"
OUT_FILE = DATA_DIR / "latent_label_scores.json"
HIDDEN_OUT = DATA_DIR / "all_location_hidden_12.npz"


def display_path(path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_DIR)
    except ValueError:
        return resolved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS_FILE)
    parser.add_argument("--model", type=Path, default=MODEL_FILE)
    parser.add_argument("--out", type=Path, default=OUT_FILE)
    parser.add_argument("--hidden-out", type=Path, default=HIDDEN_OUT)
    args = parser.parse_args()

    data = np.load(args.embeddings, allow_pickle=True)
    checkpoint = torch.load(args.model, weights_only=False)
    paths = data["paths"].tolist()

    latitudes = data["latitudes"].astype(np.float32)[:, None] / 90.0
    longitudes = data["longitudes"].astype(np.float32)[:, None] / 180.0
    x = np.concatenate([data["embeddings"].astype(np.float32), latitudes, longitudes], axis=1)
    x = (x - checkpoint["input_mean"]) / checkpoint["input_std"]
    x_tensor = torch.tensor(x, dtype=torch.float32)

    model, _ = build_model(
        checkpoint["model_name"],
        checkpoint["model_type"],
        checkpoint["model_dims"],
        x.shape[1],
        output_dim=len(checkpoint["dimensions"]),
        dropout=0,
    )
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    with torch.no_grad():
        pred = model(x_tensor).cpu().numpy() * 10.0
        hidden = model.encode(x_tensor).cpu().numpy().astype(np.float32)

    dimensions = checkpoint["dimensions"]
    output = {
        path: {dimension: round(float(value), 3) for dimension, value in zip(dimensions, row)}
        for path, row in zip(paths, pred)
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    np.savez_compressed(args.hidden_out, paths=np.array(paths, dtype=object), hidden=hidden)
    print(f"Wrote {len(paths)} predictions to {display_path(args.out)}")
    print(f"Wrote hidden vectors to {display_path(args.hidden_out)}")


if __name__ == "__main__":
    main()
