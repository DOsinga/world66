#!/usr/bin/env python3
"""
Mark a content page as "done" for a given todo task.

Adds (or updates) an entry in the `done:` dict in the page's YAML frontmatter:

    ---
    title: Some Place
    ...
    done:
      location_cleanup: 2026-04-05
    ---

Usage:
    python3 tools/mark_done.py <task_name> <path/to/page.md> [<path/to/page.md> ...]

The date defaults to today (local date). Pass --date YYYY-MM-DD to override.
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

import frontmatter


def mark_done(path: Path, task: str, date: dt.date) -> str:
    post = frontmatter.load(path)
    done = post.get("done")
    if done is None:
        done = {}
    if not isinstance(done, dict):
        raise ValueError(f"{path}: existing `done` field is not a mapping")
    action = "updated" if task in done else "added"
    done[task] = date
    post["done"] = done
    # sort_keys=False preserves existing field order in the frontmatter.
    path.write_text(frontmatter.dumps(post, sort_keys=False) + "\n", encoding="utf-8")
    return action


def main() -> int:
    ap = argparse.ArgumentParser(description="Mark a content page done for a todo task.")
    ap.add_argument("task", help="Task name (e.g. location_cleanup)")
    ap.add_argument("paths", nargs="+", type=Path, help="Path(s) to markdown file(s)")
    ap.add_argument(
        "--date",
        default=dt.date.today().isoformat(),
        help="Date (YYYY-MM-DD), default today",
    )
    args = ap.parse_args()

    try:
        date = dt.date.fromisoformat(args.date)
    except ValueError:
        print(f"Invalid --date: {args.date!r} (expected YYYY-MM-DD)", file=sys.stderr)
        return 2

    rc = 0
    for p in args.paths:
        if not p.exists():
            print(f"{p}: not found", file=sys.stderr)
            rc = 1
            continue
        try:
            action = mark_done(p, args.task, date)
            print(f"{action}: {p} ({args.task}={date.isoformat()})")
        except Exception as e:
            print(f"{p}: {e}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
