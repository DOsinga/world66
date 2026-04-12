#!/usr/bin/env python3
"""Add section and neighbourhood tags to POI files for a city."""

import sys
from pathlib import Path

import frontmatter


SECTION_TYPES = {'section', 'section_group'}
LOCATION_TYPES = {'location', 'neighbourhood'}


def get_type(path: Path) -> str | None:
    """Return the type field from a markdown file's frontmatter."""
    try:
        post = frontmatter.load(path)
        return post.metadata.get('type')
    except Exception:
        return None


def tag_pois_in_dir(section_dir: Path, tags: list[str], dry_run: bool = False) -> int:
    """Add tags to all POI .md files in a directory. Returns count of files modified."""
    count = 0
    for poi_path in sorted(section_dir.glob('*.md')):
        post = frontmatter.load(poi_path)
        existing_tags = post.metadata.get('tags', [])
        if isinstance(existing_tags, str):
            existing_tags = [existing_tags]
        new_tags = existing_tags + [t for t in tags if t not in existing_tags]
        if new_tags == existing_tags:
            continue
        post.metadata['tags'] = new_tags
        if not dry_run:
            frontmatter.dump(post, poi_path)
        print(f'  Tagged {poi_path.name}: {new_tags}')
        count += 1
    return count


def process_city(city_path: Path, dry_run: bool = False) -> None:
    """Process all section directories in a city, tagging POIs."""
    assert city_path.is_dir(), f'Not a directory: {city_path}'

    for entry in sorted(city_path.iterdir()):
        if not entry.is_dir():
            continue

        section_slug = entry.name
        section_md = city_path / f'{section_slug}.md'

        # Check if this is a top-level section directory
        if section_md.exists():
            section_type = get_type(section_md)
            if section_type in SECTION_TYPES:
                # Simple section: tag POIs with section slug
                print(f'Section [{section_slug}]:')
                tag_pois_in_dir(entry, [section_slug], dry_run)
            elif section_type in LOCATION_TYPES:
                # Neighbourhood/location: process sub-sections with neighbourhood tag
                neighbourhood_slug = section_slug
                print(f'Neighbourhood [{neighbourhood_slug}]:')
                for sub_entry in sorted(entry.iterdir()):
                    if not sub_entry.is_dir():
                        continue
                    sub_slug = sub_entry.name
                    sub_md = entry / f'{sub_slug}.md'
                    sub_type = get_type(sub_md) if sub_md.exists() else 'section'
                    if sub_type in SECTION_TYPES or sub_md.exists() is False:
                        tags = [sub_slug, neighbourhood_slug]
                        print(f'  Sub-section [{sub_slug}]:')
                        tag_pois_in_dir(sub_entry, tags, dry_run)
        else:
            # No matching .md — treat as implicit section directory
            print(f'Implicit section [{section_slug}]:')
            tag_pois_in_dir(entry, [section_slug], dry_run)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <city_content_path> [--dry-run]')
        sys.exit(1)
    city = Path(sys.argv[1])
    dry = '--dry-run' in sys.argv
    process_city(city, dry_run=dry)
