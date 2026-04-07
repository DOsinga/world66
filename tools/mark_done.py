#!/usr/bin/env python3
"""Mark a task as done in a page's frontmatter."""

import sys
from datetime import date
from pathlib import Path

import frontmatter


def mark_done(task: str, page_path: str) -> None:
    """Add task: <today> to the done: dict in the page's frontmatter."""
    path = Path(page_path)
    assert path.exists(), f'File not found: {path}'

    post = frontmatter.load(path)
    done = post.metadata.get('done', {})
    if not isinstance(done, dict):
        done = {}
    done[task] = str(date.today())
    post.metadata['done'] = done
    frontmatter.dump(post, path)
    print(f'Marked {task} done in {path}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <task> <path/to/page.md>')
        sys.exit(1)
    mark_done(sys.argv[1], sys.argv[2])
