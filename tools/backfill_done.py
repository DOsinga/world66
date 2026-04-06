#!/usr/bin/env python3
"""
Backfill `done:` stamps in content frontmatter from merged todo PRs.

Walks all merged PRs whose branch matches `todo-<task>-<shard>`, reads the
batch file from the commit just before the PR was squash-merged, resolves
each listed content path to its top-level markdown file, and (optionally)
calls mark_done to stamp it with the PR's merge date.

Dry-run by default; pass --apply to actually modify files.
Without --pr, processes all matching PRs.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"
MARK_DONE = REPO_ROOT / "tools" / "mark_done.py"

BRANCH_RE = re.compile(r"^todo-(.+)-([^-]+)$")


def run(cmd, check=True):
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def list_merged_todo_prs():
    out = run([
        "gh", "pr", "list", "--state", "merged", "--search", "todo-",
        "--limit", "500",
        "--json", "number,headRefName,mergedAt,mergeCommit",
    ]).stdout
    prs = []
    for pr in json.loads(out):
        m = BRANCH_RE.match(pr["headRefName"])
        if not m:
            continue
        prs.append({
            "number": pr["number"],
            "branch": pr["headRefName"],
            "task": m.group(1),
            "shard": m.group(2),
            "merged_at": pr["mergedAt"][:10],  # YYYY-MM-DD
            "sha": pr["mergeCommit"]["oid"],
        })
    # Oldest first for stable commit order.
    prs.sort(key=lambda p: p["merged_at"])
    return prs


def read_batch_file(sha, task, shard):
    """Read the batch file as it existed just before the merge commit.

    Some PRs re-ran an already-deleted shard or didn't delete the batch file
    themselves; fall back to the commit that originally added the file.
    """
    path = f"todo/{task}/{shard}.txt"
    result = run(["git", "show", f"{sha}^:{path}"], check=False)
    if result.returncode == 0:
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    # Fallback: find the commit that added this path across all history.
    log = run(
        ["git", "log", "--all", "--diff-filter=A", "--format=%H", "--", path],
        check=False,
    ).stdout.strip().splitlines()
    if not log:
        return None
    add_sha = log[-1]  # oldest addition
    result = run(["git", "show", f"{add_sha}:{path}"], check=False)
    if result.returncode != 0:
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def resolve_item(content_path):
    """Resolve a content path (e.g. 'europe/italy/tuscany/forte_dei_marmi')
    to its top-level markdown file.

    Priority:
      1. <path>/<slug>.md  (dir-with-index form)
      2. <path>.md         (flat form)
    """
    p = content_path.strip().strip("/")
    if not p:
        return None
    slug = p.rsplit("/", 1)[-1]
    candidates = [
        CONTENT_DIR / p / f"{slug}.md",
        CONTENT_DIR / f"{p}.md",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def process_pr(pr, apply):
    items = read_batch_file(pr["sha"], pr["task"], pr["shard"])
    if items is None:
        return {"pr": pr, "status": "no-batch-file", "resolved": [], "missing": []}

    resolved = []
    missing = []
    for item in items:
        md = resolve_item(item)
        if md is None:
            missing.append(item)
        else:
            resolved.append(md)

    if apply and resolved:
        cmd = [
            sys.executable, str(MARK_DONE),
            pr["task"],
            "--date", pr["merged_at"],
        ] + [str(p) for p in resolved]
        r = run(cmd, check=False)
        if r.returncode != 0:
            return {"pr": pr, "status": "mark_done-failed", "resolved": resolved,
                    "missing": missing, "stderr": r.stderr}

        # Commit this PR's backfill. Use `git add` with explicit paths to
        # avoid picking up unrelated working-tree changes.
        run(["git", "add"] + [str(p) for p in resolved])
        status = run(["git", "status", "--porcelain"]).stdout
        if status.strip():
            msg = (
                f"Backfill done stamps for {pr['branch']} (#{pr['number']})\n\n"
                f"{pr['task']}: {pr['merged_at']} — {len(resolved)} items"
            )
            c = run(["git", "commit", "-m", msg], check=False)
            if c.returncode != 0:
                return {"pr": pr, "status": "commit-failed", "resolved": resolved,
                        "missing": missing, "stderr": c.stderr}

    return {"pr": pr, "status": "ok", "resolved": resolved, "missing": missing}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually modify files (default: dry-run)")
    ap.add_argument("--pr", type=int, help="Process only this PR number")
    ap.add_argument("--task", help="Process only this task name")
    args = ap.parse_args()

    prs = list_merged_todo_prs()
    if args.pr:
        prs = [p for p in prs if p["number"] == args.pr]
    if args.task:
        prs = [p for p in prs if p["task"] == args.task]

    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(prs)} PRs")
    total_resolved = 0
    total_missing = 0
    task_counts = {}
    for pr in prs:
        result = process_pr(pr, args.apply)
        n_res = len(result["resolved"])
        n_miss = len(result["missing"])
        total_resolved += n_res
        total_missing += n_miss
        task_counts[pr["task"]] = task_counts.get(pr["task"], 0) + n_res
        print(f"  #{pr['number']:>3} {pr['branch']:<45} {result['status']:<18} {n_res:>3} items, {n_miss} missing")
        if result["missing"]:
            for m in result["missing"]:
                print(f"      MISSING: {m}")
        if result["status"] == "mark_done-failed":
            print(f"      STDERR: {result['stderr']}")

    print()
    print(f"Total items resolved: {total_resolved}")
    print(f"Total items missing:  {total_missing}")
    print(f"By task: {task_counts}")


if __name__ == "__main__":
    main()
