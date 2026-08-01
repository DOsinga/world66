#!/usr/bin/env python3

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "scoring" / "data"
BATCH_DIR = DATA_DIR / "batches"
SCORE_DIR = DATA_DIR / "agent_scores"
SCORING_DOC = PROJECT_DIR / "scoring" / "SCORING.md"
DIMENSIONS = ("heritage", "vibrancy", "nature", "leisure", "adventure")


def scoring_guidelines():
    text = SCORING_DOC.read_text()
    start = text.index("## Scoring Guidelines")
    end = text.index("## Files")
    return text[start:end].strip()


def compact_batch(batch):
    return [
        {
            "id": index,
            "path": item["path"],
            "name": item["name"],
            "parent_chain": item["parent_chain"],
            "latitude": item["latitude"],
            "longitude": item["longitude"],
        }
        for index, item in enumerate(batch)
    ]


def clean_score(value):
    score = int(value)
    if score < 0 or score > 10:
        raise ValueError(f"score outside 0..10: {value}")
    return score


def clean_scores(batch, scores):
    paths = {item["path"] for item in batch}
    if set(scores) == paths:
        keyed_scores = scores
    else:
        expected_ids = {str(index) for index in range(len(batch))}
        actual_ids = set(scores)
        if expected_ids != actual_ids:
            missing = sorted(expected_ids - actual_ids)
            extra = sorted(actual_ids - expected_ids)
            raise ValueError(f"ids mismatch missing={missing[:3]} extra={extra[:3]}")
        keyed_scores = {
            batch[int(index)]["path"]: row
            for index, row in scores.items()
        }

    cleaned = {}
    for path, row in keyed_scores.items():
        missing = [dimension for dimension in DIMENSIONS if dimension not in row]
        extra = [dimension for dimension in row if dimension not in DIMENSIONS]
        if missing or extra:
            raise ValueError(f"{path} has missing={missing} extra={extra}")
        cleaned[path] = {dimension: clean_score(row[dimension]) for dimension in DIMENSIONS}
    return cleaned


def get_client(env_file):
    load_dotenv(env_file or PROJECT_DIR / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set. Add it to .env or pass --env-file.")
    return OpenAI()


def score_batch(client, model, batch):
    prompt = {
        "instructions": scoring_guidelines(),
        "output_format": {
            "type": "object",
            "description": "JSON object keyed by location id as a string. Each value has integer scores for heritage, vibrancy, nature, leisure, adventure.",
        },
        "locations": compact_batch(batch),
    }
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You score travel destinations for World66. Return only valid JSON.",
            },
            {
                "role": "user",
                "content": json.dumps(prompt, separators=(",", ":")),
            },
        ],
    )
    return json.loads(response.choices[0].message.content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=Path, default=BATCH_DIR)
    parser.add_argument("--out-dir", type=Path, default=SCORE_DIR)
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    batch_files = sorted(args.batches.glob("batch_*.json"))
    if args.limit:
        batch_files = batch_files[: args.limit]
    if not batch_files:
        raise SystemExit(f"No batch files found in {args.batches}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    def run_one(index, batch_file):
        out_file = args.out_dir / batch_file.name
        if out_file.exists() and not args.replace:
            return f"skip {out_file.relative_to(PROJECT_DIR)}"

        client = get_client(args.env_file)
        batch = json.loads(batch_file.read_text())
        for attempt in range(args.retries + 1):
            try:
                raw_scores = score_batch(client, args.model, batch)
                scores = clean_scores(batch, raw_scores)
                out_file.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")
                return f"scored {index}/{len(batch_files)} {batch_file.name}"
            except Exception as exc:
                if attempt >= args.retries:
                    raise
                wait = 2 ** attempt
                print(f"retry {batch_file.name}: {exc}", flush=True)
                time.sleep(wait)
        time.sleep(args.sleep)

    if args.workers == 1:
        for index, batch_file in enumerate(batch_files, start=1):
            print(run_one(index, batch_file), flush=True)
        return

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(run_one, index, batch_file)
            for index, batch_file in enumerate(batch_files, start=1)
        ]
        for future in as_completed(futures):
            print(future.result(), flush=True)


if __name__ == "__main__":
    main()
