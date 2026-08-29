#!/usr/bin/env python3

import argparse
import json
import math
import random
import sys
from pathlib import Path

import frontmatter

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = PROJECT_DIR / "content"
SCORING_DIR = PROJECT_DIR / "scoring"
DATA_DIR = SCORING_DIR / "data"
SAMPLE_FILE = DATA_DIR / "sample_2000.json"
BATCH_DIR = DATA_DIR / "batches"
AGENT_SCORE_DIR = DATA_DIR / "agent_scores"
RESCORE_BATCH_DIR = DATA_DIR / "rescore_batches"
RESCORE_DIR = DATA_DIR / "rescores"
SCORED_FILE = DATA_DIR / "scored_2000.json"
ALL_LOCATIONS_FILE = DATA_DIR / "all_locations.json"

CONTINENTS = {
    "africa",
    "antarctica",
    "asia",
    "australiaandpacific",
    "europe",
    "northamerica",
    "southamerica",
}
SCORABLE_LOC_TYPES = {"city", "feature", "island"}
DIMENSIONS = ("heritage", "vibrancy", "nature", "off_the_beaten_track")


def content_path_for(md_file):
    rel = md_file.relative_to(CONTENT_DIR)
    if md_file.parent.name == md_file.stem:
        return rel.parent.as_posix()
    return rel.with_suffix("").as_posix()


def load_meta(md_file):
    return frontmatter.load(md_file).metadata


def title_from_path(path):
    return path.rsplit("/", 1)[-1].replace("_", " ").title()


def ancestor_title(parts, depth):
    md_file = CONTENT_DIR.joinpath(*parts[:depth]).with_suffix(".md")
    if not md_file.exists():
        return parts[depth - 1].replace("_", " ").title()
    meta = load_meta(md_file)
    return meta.get("title") or title_from_path(md_file.stem)


def parent_chain_for(path):
    parts = Path(path).parts
    return [ancestor_title(parts, i) for i in range(1, len(parts))]


def as_float(value):
    if value is None:
        return None
    return float(value)


def discover_locations():
    locations = []
    for md_file in sorted(CONTENT_DIR.rglob("*.md")):
        rel = md_file.relative_to(CONTENT_DIR)
        if not rel.parts or rel.parts[0] not in CONTINENTS:
            continue

        meta = load_meta(md_file)
        if meta.get("type") != "location":
            continue
        if meta.get("loc_type") not in SCORABLE_LOC_TYPES:
            continue

        lat = as_float(meta.get("latitude"))
        lng = as_float(meta.get("longitude"))
        if lat is None or lng is None:
            continue

        path = content_path_for(md_file)
        title = meta.get("title") or title_from_path(path)
        parent_chain = parent_chain_for(path)
        parent = ", ".join(parent_chain)
        locations.append(
            {
                "path": path,
                "name": title,
                "parent": parent,
                "parent_chain": parent_chain,
                "latitude": lat,
                "longitude": lng,
                "lat": lat,
                "lng": lng,
                "url": "/" + path + "/",
                "embedding_text": f"{title}, {', '.join(reversed(parent_chain))}",
            }
        )
    return locations


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def display_path(path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_DIR)
    except ValueError:
        return resolved


def cmd_sample(args):
    locations = discover_locations()
    if len(locations) < args.n:
        print(f"Only found {len(locations)} scorable locations with coordinates.", file=sys.stderr)
        sys.exit(2)

    rng = random.Random(args.seed)
    sample = rng.sample(locations, args.n)
    write_json(args.out, sample)
    print(f"Wrote {len(sample)} locations to {display_path(args.out)}")


def cmd_expand_sample(args):
    existing = json.loads(args.sample.read_text())
    existing_paths = {item["path"] for item in existing}
    locations = [item for item in discover_locations() if item["path"] not in existing_paths]
    needed = args.n - len(existing)
    if needed <= 0:
        print(f"{display_path(args.sample)} already has {len(existing)} locations")
        return
    if len(locations) < needed:
        print(f"Only found {len(locations)} new locations, need {needed}.", file=sys.stderr)
        sys.exit(2)

    rng = random.Random(args.seed)
    expanded = existing + rng.sample(locations, needed)
    write_json(args.sample, expanded)
    print(f"Expanded {display_path(args.sample)} to {len(expanded)} locations")


def cmd_export_locations(args):
    locations = discover_locations()
    write_json(args.out, locations)
    print(f"Wrote {len(locations)} locations to {display_path(args.out)}")


def cmd_batches(args):
    sample = json.loads(args.sample.read_text())
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for old_batch in args.out_dir.glob("batch_*.json"):
        old_batch.unlink()

    count = 0
    for i in range(0, len(sample), args.size):
        batch = sample[i : i + args.size]
        write_json(args.out_dir / f"batch_{count:03d}.json", batch)
        count += 1

    print(f"Wrote {count} batches to {display_path(args.out_dir)}")


def cmd_rescore_batches(args):
    sample = {item["path"]: item for item in json.loads(args.sample.read_text())}
    scored = json.loads(args.scored.read_text())
    paths = sorted(scored)

    missing = [path for path in paths if path not in sample]
    if missing:
        raise ValueError(f"{args.scored} contains paths outside sample: {', '.join(missing[:5])}")

    rng = random.Random(args.seed)
    rng.shuffle(paths)

    RESCORE_BATCH_DIR.mkdir(parents=True, exist_ok=True)
    for old_batch in RESCORE_BATCH_DIR.glob("rescore_*.json"):
        old_batch.unlink()

    count = 0
    for i in range(0, len(paths), args.size):
        batch = [sample[path] for path in paths[i : i + args.size]]
        write_json(RESCORE_BATCH_DIR / f"rescore_{count:03d}.json", batch)
        count += 1

    print(f"Wrote {count} rescore batches to {RESCORE_BATCH_DIR.relative_to(PROJECT_DIR)}")


def load_agent_scores(path):
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def clean_score(raw):
    value = int(raw)
    if value < 0 or value > 10:
        raise ValueError(f"score {value} outside 0..10")
    return value


def clean_scores(path, scores):
    cleaned = {}
    for item_path, item_scores in scores.items():
        missing = [d for d in DIMENSIONS if d not in item_scores]
        extra = [d for d in item_scores if d not in DIMENSIONS]
        if missing or extra:
            raise ValueError(f"{path}: {item_path} has missing={missing} extra={extra}")
        cleaned[item_path] = {dimension: clean_score(item_scores[dimension]) for dimension in DIMENSIONS}
    return cleaned


def cmd_merge(args):
    merged = {}
    if args.out.exists() and not args.fresh:
        merged = json.loads(args.out.read_text())

    args.scores_dir.mkdir(parents=True, exist_ok=True)
    for score_file in sorted(args.scores_dir.glob("batch_*.json")):
        scores = clean_scores(score_file, load_agent_scores(score_file))
        overlap = sorted(set(merged) & set(scores))
        if overlap and not args.replace:
            joined = ", ".join(overlap[:5])
            raise ValueError(f"{score_file} overlaps existing scores: {joined}")
        merged.update(scores)

    write_json(args.out, dict(sorted(merged.items())))
    print(f"Wrote {len(merged)} scored locations to {args.out.resolve().relative_to(PROJECT_DIR)}")


def cmd_validate(args):
    sample = {item["path"] for item in json.loads(args.sample.read_text())}
    scored = clean_scores(args.scored, json.loads(args.scored.read_text()))
    unknown = sorted(set(scored) - sample)
    if unknown:
        raise ValueError(f"scored.json contains paths outside sample: {', '.join(unknown[:5])}")

    print(f"{len(scored)} valid scored locations")
    print(f"{len(sample) - len(scored)} sample locations still unscored")


def mean(values):
    return sum(values) / len(values)


def correlation(xs, ys):
    x_mean = mean(xs)
    y_mean = mean(ys)
    x_var = sum((x - x_mean) ** 2 for x in xs)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    if not x_var or not y_var:
        return 0
    cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    return cov / math.sqrt(x_var * y_var)


def load_many_scores(directory, pattern):
    scores = {}
    for score_file in sorted(directory.glob(pattern)):
        scores.update(clean_scores(score_file, load_agent_scores(score_file)))
    return scores


def cmd_compare(args):
    original = clean_scores(args.original, json.loads(args.original.read_text()))
    rescores = load_many_scores(args.rescores, "rescore_*.json")
    paths = sorted(set(original) & set(rescores))
    if not paths:
        raise ValueError("No overlapping scores to compare")

    print(f"overlap: {len(paths)} locations")
    for dimension in DIMENSIONS:
        xs = [original[path][dimension] for path in paths]
        ys = [rescores[path][dimension] for path in paths]
        diffs = [abs(x - y) for x, y in zip(xs, ys)]
        print(
            f"{dimension}: mean_abs_diff={mean(diffs):.2f} "
            f"max_abs_diff={max(diffs)} corr={correlation(xs, ys):.2f}"
        )

    disagreements = []
    for path in paths:
        diff = sum(abs(original[path][dimension] - rescores[path][dimension]) for dimension in DIMENSIONS)
        disagreements.append((diff, path, original[path], rescores[path]))

    print("\nbiggest disagreements:")
    for diff, path, old, new in sorted(disagreements, reverse=True)[: args.top]:
        print(f"{diff:>2} {path} original={old} rescore={new}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("sample")
    sample.add_argument("--n", type=int, default=1000)
    sample.add_argument("--seed", type=int, default=66)
    sample.add_argument("--out", type=Path, default=SAMPLE_FILE)
    sample.set_defaults(func=cmd_sample)

    expand_sample = sub.add_parser("expand-sample")
    expand_sample.add_argument("--sample", type=Path, default=SAMPLE_FILE)
    expand_sample.add_argument("--n", type=int, default=2000)
    expand_sample.add_argument("--seed", type=int, default=67)
    expand_sample.set_defaults(func=cmd_expand_sample)

    export_locations = sub.add_parser("export-locations")
    export_locations.add_argument("--out", type=Path, default=ALL_LOCATIONS_FILE)
    export_locations.set_defaults(func=cmd_export_locations)

    batches = sub.add_parser("batches")
    batches.add_argument("--sample", type=Path, default=SAMPLE_FILE)
    batches.add_argument("--size", type=int, default=50)
    batches.add_argument("--out-dir", type=Path, default=BATCH_DIR)
    batches.set_defaults(func=cmd_batches)

    rescore_batches = sub.add_parser("rescore-batches")
    rescore_batches.add_argument("--sample", type=Path, default=SAMPLE_FILE)
    rescore_batches.add_argument("--scored", type=Path, default=SCORED_FILE)
    rescore_batches.add_argument("--size", type=int, default=40)
    rescore_batches.add_argument("--seed", type=int, default=67)
    rescore_batches.set_defaults(func=cmd_rescore_batches)

    merge = sub.add_parser("merge")
    merge.add_argument("--fresh", action="store_true")
    merge.add_argument("--replace", action="store_true")
    merge.add_argument("--scores-dir", type=Path, default=AGENT_SCORE_DIR)
    merge.add_argument("--out", type=Path, default=SCORED_FILE)
    merge.set_defaults(func=cmd_merge)

    validate = sub.add_parser("validate")
    validate.add_argument("--sample", type=Path, default=SAMPLE_FILE)
    validate.add_argument("--scored", type=Path, default=SCORED_FILE)
    validate.set_defaults(func=cmd_validate)

    compare = sub.add_parser("compare")
    compare.add_argument("--original", type=Path, default=SCORED_FILE)
    compare.add_argument("--rescores", type=Path, default=RESCORE_DIR)
    compare.add_argument("--top", type=int, default=20)
    compare.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
