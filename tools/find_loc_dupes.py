#!/usr/bin/env python3
"""Find directories that contain a markdown file with the same name as the directory.

E.g. `foo/foo.md` — which is the wrong structure. The normal pattern is `foo.md`
alongside a `foo/` directory.

For each hit, report whether the sibling `foo.md` also exists (both) or not.
"""

from pathlib import Path

CONTENT = Path('content')


def main() -> None:
    hits = []
    for md in CONTENT.rglob('*.md'):
        # md is e.g. content/a/b/foo/foo.md
        if md.stem == md.parent.name:
            sibling = md.parent.with_suffix('.md')
            kind = 'both' if sibling.exists() else 'nested-only'
            hits.append((kind, str(md)))

    hits.sort()
    for kind, path in hits:
        print(f'{kind}\t{path}')
    print(f'\n# total: {len(hits)}')


if __name__ == '__main__':
    main()
