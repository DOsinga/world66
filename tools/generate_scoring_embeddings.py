#!/usr/bin/env python3

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCORING_DIR = PROJECT_DIR / "scoring"
SAMPLE_FILE = SCORING_DIR / "sample_1000.json"
DEFAULT_OUT = SCORING_DIR / "location_embeddings.npz"
DEFAULT_META_OUT = SCORING_DIR / "location_embeddings_meta.json"
DEFAULT_MODEL = "text-embedding-3-small"


def embedding_text(item):
    parents = ", ".join(reversed(item["parent_chain"]))
    return f"{item['name']}, {parents} ({item['latitude']:.6f}, {item['longitude']:.6f})"


def load_sample(path):
    items = json.loads(path.read_text())
    for item in items:
        item["embedding_text"] = embedding_text(item)
    return items


def batched(items, size):
    for i in range(0, len(items), size):
        yield i, items[i : i + size]


def existing_paths(path):
    if not path.exists():
        return set()
    data = np.load(path, allow_pickle=True)
    return set(data["paths"].tolist())


def save_embeddings(path, meta_path, source_path, items, vectors, model):
    path = path.resolve()
    meta_path = meta_path.resolve()
    paths = np.array([item["path"] for item in items], dtype=object)
    texts = np.array([item["embedding_text"] for item in items], dtype=object)
    latitudes = np.array([item["latitude"] for item in items], dtype=np.float32)
    longitudes = np.array([item["longitude"] for item in items], dtype=np.float32)
    embeddings = np.array(vectors, dtype=np.float32)

    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        embeddings=embeddings,
        paths=paths,
        texts=texts,
        latitudes=latitudes,
        longitudes=longitudes,
    )
    meta_path.write_text(
        json.dumps(
            {
                "model": model,
                "count": len(items),
                "dimensions": int(embeddings.shape[1]) if len(items) else 0,
                "source": str(source_path.resolve().relative_to(PROJECT_DIR)),
                "output": str(path.relative_to(PROJECT_DIR)),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def get_client(args):
    if args.env_file:
        load_dotenv(args.env_file)
    else:
        load_dotenv(PROJECT_DIR / ".env")

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set. Add it to the environment or pass --env-file.")
    return OpenAI()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, default=SAMPLE_FILE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--meta-out", type=Path, default=DEFAULT_META_OUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    items = load_sample(args.sample)
    if args.dry_run:
        print(f"Would embed {len(items)} locations with {args.model}.")
        print(f"First: {items[0]['embedding_text']}")
        print(f"Last:  {items[-1]['embedding_text']}")
        return

    already = existing_paths(args.out)
    if already:
        print(f"{args.out} already contains {len(already)} embeddings; regenerating all.")

    client = get_client(args)
    vectors = []
    total_tokens = 0
    for start, batch in batched(items, args.batch_size):
        response = client.embeddings.create(
            model=args.model,
            input=[item["embedding_text"] for item in batch],
            encoding_format="float",
        )
        vectors.extend(row.embedding for row in sorted(response.data, key=lambda row: row.index))
        total_tokens += response.usage.total_tokens
        print(f"embedded {start + len(batch)}/{len(items)}")
        time.sleep(0.1)

    save_embeddings(args.out, args.meta_out, args.sample, items, vectors, args.model)
    print(f"Wrote {len(vectors)} embeddings to {args.out.resolve().relative_to(PROJECT_DIR)}")
    print(f"Total tokens: {total_tokens}")


if __name__ == "__main__":
    main()
