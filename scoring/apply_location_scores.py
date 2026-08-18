#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import frontmatter

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = PROJECT_DIR / "content"
DATA_DIR = PROJECT_DIR / "scoring" / "data"
LOCATION_SCORES_FILE = DATA_DIR / "location_scores.json"
FIELDS = ("score", "heritage", "vibrancy", "nature", "off_the_beaten_track")


def load_json(path):
    return json.loads(path.read_text())


def display_path(path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_DIR)
    except ValueError:
        return resolved


def md_path_for(content_path):
    directory_style = CONTENT_DIR / content_path / f"{Path(content_path).name}.md"
    if directory_style.exists():
        return directory_style
    return CONTENT_DIR / f"{content_path}.md"


def normalize(value):
    return round(float(value), 3)


def apply_scores(scores, dry_run):
    changed = []
    skipped = []
    for content_path, row in sorted(scores.items()):
        md_path = md_path_for(content_path)
        if not md_path.exists():
            skipped.append((content_path, "missing markdown"))
            continue

        post = frontmatter.load(md_path)
        if post.metadata.get("type", "location") != "location":
            skipped.append((content_path, "not a location page"))
            continue

        updates = {field: normalize(row[field]) for field in FIELDS}
        if all(post.metadata.get(field) == value for field, value in updates.items()):
            continue

        post.metadata.update(updates)
        changed.append(md_path)
        if not dry_run:
            md_path.write_text(frontmatter.dumps(post, sort_keys=False) + "\n", encoding="utf-8")

    return changed, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=LOCATION_SCORES_FILE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    scores = load_json(args.scores)
    changed, skipped = apply_scores(scores, args.dry_run)
    verb = "Would update" if args.dry_run else "Updated"
    print(f"{verb} {len(changed)} location markdown files from {display_path(args.scores)}")
    if skipped:
        print(f"Skipped {len(skipped)} score rows")
        for content_path, reason in skipped[:20]:
            print(f"- {content_path}: {reason}")


if __name__ == "__main__":
    main()
