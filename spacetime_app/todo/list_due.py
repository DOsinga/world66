#!/usr/bin/env python3
"""
Print sources that are due for a check, sorted by most overdue first.

Usage:
    venv/bin/python spacetime_app/todo/list_due.py
    venv/bin/python spacetime_app/todo/list_due.py --all   # include not-yet-due
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import frontmatter

SOURCES_DIR = Path(__file__).parent.parent / "sources"


def main():
    show_all = "--all" in sys.argv
    today = date.today()
    rows = []

    for path in sorted(SOURCES_DIR.glob("*.md")):
        try:
            post = frontmatter.load(str(path))
        except Exception as e:
            print(f"  ERROR reading {path.name}: {e}", file=sys.stderr)
            continue

        slug = path.stem
        url = post.get("url", "")
        poi = post.get("poi", "")
        interval = int(post.get("interval_days", 7))
        last_checked = post.get("last_checked")

        if last_checked is None:
            due_since = today  # never checked — due now
        else:
            if hasattr(last_checked, "date"):
                last_checked = last_checked.date()
            elif isinstance(last_checked, str):
                last_checked = date.fromisoformat(last_checked)
            due_since = last_checked + timedelta(days=interval)

        days_overdue = (today - due_since).days
        is_due = days_overdue >= 0

        if is_due or show_all:
            rows.append((days_overdue, slug, poi, url, last_checked))

    if not rows:
        print("No sources due for checking today.")
        return

    rows.sort(reverse=True)
    print(f"{'SLUG':<40} {'POI':<50} {'OVERDUE':>8}  {'LAST CHECKED'}")
    print("-" * 120)
    for days_overdue, slug, poi, url, last_checked in rows:
        overdue_str = f"{days_overdue}d" if days_overdue >= 0 else f"in {-days_overdue}d"
        lc = str(last_checked) if last_checked else "never"
        print(f"{slug:<40} {poi:<50} {overdue_str:>8}  {lc}")


if __name__ == "__main__":
    main()
