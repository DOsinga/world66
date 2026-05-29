#!/usr/bin/env python3
"""Migrate city section folders into tags on POIs."""

import subprocess
import sys
from pathlib import Path

import frontmatter

REPO = Path('/Users/douwe/Dropbox/Douwe/Proj/World66')
CONTENT = REPO / 'content'

# Known section slugs (directories that are sections, not neighbourhoods)
SECTION_SLUGS = {
    'things_to_do', 'shopping', 'eating_out', 'bars_and_cafes',
    'nightlife', 'entertainment', 'sights', 'activities',
    'getting_there', 'getting_around', 'when_to_go', 'day_trips',
    'practical_info', 'where_to_eat', 'where_to_drink',
    'arts_and_culture', 'sport', 'sports', 'outdoors',
    'beaches', 'nature', 'museums', 'parks',
    'books', 'top_5_must_dos', 'itineraries', 'stories',
    'tours_and_excursio', 'orientation', 'history',
    'festivals', 'nightlife_and_ente', 'cybercafs',
    'practical_informat', 'budget_travel_idea', 'family_travel_idea',
    'day_guides', 'eatingout', 'people', 'restaurants',
    'sights',
}


def git(args: list[str]) -> str:
    """Run a git command in the repo."""
    result = subprocess.run(
        ['git', '-C', str(REPO)] + args,
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


# Normalize section slugs to canonical tag names
SLUG_NORMALIZE = {
    'eatingout': 'eating_out',
    'restaurants': 'eating_out',
    'where_to_eat': 'eating_out',
    'where_to_drink': 'bars_and_cafes',
    'nightlife': 'bars_and_cafes',
    'nightlife_and_ente': 'bars_and_cafes',
    'sights': 'things_to_do',
    'activities': 'things_to_do',
    'museums': 'things_to_do',
    'arts_and_culture': 'things_to_do',
    'sport': 'things_to_do',
    'sports': 'things_to_do',
    'outdoors': 'things_to_do',
    'nature': 'things_to_do',
    'parks': 'things_to_do',
}


def normalize_section_tag(slug: str) -> str:
    """Normalize a section slug to its canonical tag name."""
    return SLUG_NORMALIZE.get(slug, slug)


def is_section_dir(dir_path: Path) -> bool:
    """Check if a directory is a section (has a matching .md sibling or slug matches known sections)."""
    slug = dir_path.name
    return slug in SECTION_SLUGS


def get_poi_files(section_dir: Path) -> list[Path]:
    """Get all POI .md files from a directory (non-recursive for sections)."""
    return [f for f in section_dir.iterdir() if f.suffix == '.md' and f.is_file()]


def get_poi_files_recursive(section_dir: Path) -> list[Path]:
    """Get all POI .md files recursively from a directory."""
    return list(section_dir.rglob('*.md'))


def infer_type_tags(post, section_slug: str) -> list[str]:
    """Infer type tags based on section, title, and content."""
    title = post.metadata.get('title', '').lower()
    body = post.content.lower() if post.content else ''
    tags = []

    # Section-based defaults
    if section_slug in ('eating_out', 'where_to_eat'):
        tags.append('restaurant')
    elif section_slug in ('bars_and_cafes', 'where_to_drink', 'nightlife'):
        tags.append('bar')
    elif section_slug == 'shopping':
        tags.append('shop')
    elif section_slug == 'beaches':
        tags.append('beach')
    elif section_slug == 'books':
        tags.append('book')

    # Title/content keyword matching for things_to_do and other sections
    kw_map = {
        'museum': ['museum', 'gallery', 'galleria', 'pinacoteca', 'museo'],
        'church': ['church', 'cathedral', 'basilica', 'chapel', 'mosque', 'synagogue', 'temple', 'wat ', 'chiesa'],
        'palace': ['palace', 'palazzo', 'castle', 'château', 'chateau', 'fortress', 'fort ', 'citadel'],
        'park': ['park', 'garden', 'botanical', 'jardin', 'giardino'],
        'market': ['market', 'bazaar', 'souk', 'mercato', 'marché'],
        'monument': ['monument', 'memorial', 'statue', 'obelisk', 'column'],
        'bridge': ['bridge', 'ponte', 'puente'],
        'tower': ['tower', 'torre'],
        'square': ['square', 'plaza', 'piazza', 'platz'],
        'theatre': ['theatre', 'theater', 'teatro', 'opera house', 'opera'],
        'beach': ['beach', 'playa', 'spiaggia'],
        'restaurant': ['restaurant', 'trattoria', 'osteria', 'bistro', 'ristorante', 'brasserie', 'pizzeria', 'diner'],
        'cafe': ['café', 'cafe', 'coffee', 'coffeehouse', 'tea house', 'teahouse'],
        'bar': ['bar ', 'pub ', 'tavern', 'brewery', 'cocktail', 'wine bar', 'taproom'],
        'club': ['club', 'disco', 'nightclub'],
        'neighbourhood': ['neighbourhood', 'neighborhood', 'district', 'quarter'],
    }

    text = f'{title} {body[:500]}'
    for tag, keywords in kw_map.items():
        if tag in tags:
            continue
        for kw in keywords:
            if kw in text:
                tags.append(tag)
                break

    # Refine: if section is eating_out and we matched cafe, use cafe instead of restaurant
    if 'cafe' in tags and 'restaurant' in tags:
        tags.remove('restaurant')
    # If section is bars_and_cafes and we matched restaurant, drop it
    if section_slug == 'bars_and_cafes' and 'restaurant' in tags:
        tags.remove('restaurant')

    return tags


def add_tags_to_poi(poi_path: Path, section_slug: str, extra_tags: list[str] = None) -> None:
    """Add section and extra tags to a POI file."""
    post = frontmatter.load(poi_path)
    existing_tags = post.metadata.get('tags', [])
    if isinstance(existing_tags, str):
        existing_tags = [existing_tags]
    existing_tags = list(existing_tags)

    new_tags = list(existing_tags)
    if section_slug not in new_tags:
        new_tags.append(section_slug)

    # Handle neighbourhood field - convert to tag
    neighbourhood = post.metadata.get('neighbourhood', '')
    if neighbourhood:
        nb_slug = neighbourhood.lower().replace(' ', '_').replace('-', '_')
        if nb_slug not in new_tags:
            new_tags.append(nb_slug)
        del post.metadata['neighbourhood']

    for tag in (extra_tags or []):
        if tag not in new_tags:
            new_tags.append(tag)

    # Infer type tags
    for tag in infer_type_tags(post, section_slug):
        if tag not in new_tags:
            new_tags.append(tag)

    # Drop category field if present
    if 'category' in post.metadata:
        del post.metadata['category']

    post.metadata['tags'] = new_tags
    frontmatter.dump(post, poi_path)


def ensure_section_type(md_path: Path) -> None:
    """Make sure a section .md file has type: section."""
    if not md_path.exists():
        return
    post = frontmatter.load(md_path)
    if post.metadata.get('type') != 'section':
        post.metadata['type'] = 'section'
        frontmatter.dump(post, md_path)


def ensure_neighbourhood_type(md_path: Path) -> None:
    """Make sure a neighbourhood .md file has type: neighbourhood."""
    if not md_path.exists():
        return
    post = frontmatter.load(md_path)
    if post.metadata.get('type') != 'neighbourhood':
        post.metadata['type'] = 'neighbourhood'
        frontmatter.dump(post, md_path)


def create_neighbourhood_md(city_dir: Path, slug: str, title: str) -> Path:
    """Create a neighbourhood .md file if it doesn't exist."""
    nb_path = city_dir / f'{slug}.md'
    if not nb_path.exists():
        post = frontmatter.Post(
            f'Neighbourhood area of the city.',
            title=title.replace('_', ' ').title(),
            type='neighbourhood'
        )
        frontmatter.dump(post, nb_path)
    else:
        ensure_neighbourhood_type(nb_path)
    return nb_path


def migrate_city(city_path: str) -> None:
    """Migrate a single city."""
    city_dir = CONTENT / city_path
    assert city_dir.exists(), f'City directory not found: {city_dir}'

    # Find the city .md file (same name as last component)
    city_slug = city_dir.name
    city_md = city_dir.parent / f'{city_slug}.md'
    assert city_md.exists(), f'City .md not found: {city_md}'

    print(f'\n=== Processing {city_path} ===')

    # Find section and neighbourhood subdirectories
    subdirs = [d for d in city_dir.iterdir() if d.is_dir()]

    moved_files = []
    neighbourhood_slugs = set()

    for subdir in subdirs:
        slug = subdir.name
        section_md = city_dir / f'{slug}.md'

        # Skip sub-locations (type: location) — these are child cities/areas, not sections
        if section_md.exists():
            section_post = frontmatter.load(section_md)
            if section_post.metadata.get('type') == 'location':
                print(f'  Skipping sub-location: {slug}/')
                continue

        if is_section_dir(subdir):
            # It's a section directory
            ensure_section_type(section_md)
            tag = normalize_section_tag(slug)
            poi_files = get_poi_files(subdir)

            for poi_path in poi_files:
                dest = city_dir / poi_path.name
                # Avoid naming collision
                if dest.exists():
                    base = poi_path.stem
                    dest = city_dir / f'{slug}_{base}.md'
                print(f'  Moving {poi_path.name} from {slug}/ -> root (tag: {tag})')
                add_tags_to_poi(poi_path, tag)
                git(['mv', str(poi_path.relative_to(REPO)), str(dest.relative_to(REPO))])
                moved_files.append(dest)

        else:
            # It's likely a neighbourhood directory
            neighbourhood_slugs.add(slug)
            nb_md = city_dir / f'{slug}.md'
            if nb_md.exists():
                ensure_neighbourhood_type(nb_md)
            else:
                create_neighbourhood_md(city_dir, slug, slug)
                git(['add', str(nb_md.relative_to(REPO))])

            all_files = get_poi_files_recursive(subdir)

            for poi_path in all_files:
                post = frontmatter.load(poi_path)
                file_type = post.metadata.get('type', 'poi')

                # Skip section/neighbourhood files - delete them (their content is superseded)
                if file_type in ('section', 'neighbourhood'):
                    print(f'  Deleting section file {poi_path.name} from {slug}/')
                    git(['rm', str(poi_path.relative_to(REPO))])
                    continue

                # What section is this in? Check parent relative to subdir
                rel = poi_path.relative_to(subdir)
                parts = rel.parts
                section_tag = None
                if len(parts) > 1:
                    # Nested in a section inside neighbourhood
                    section_tag = parts[0] if parts[0] in SECTION_SLUGS else None

                dest = city_dir / poi_path.name
                if dest.exists():
                    dest = city_dir / f'{slug}_{poi_path.name}'

                print(f'  Moving {poi_path.name} from {slug}/ -> root (neighbourhood tag: {slug})')
                # Read and update tags
                existing_tags = post.metadata.get('tags', [])
                if isinstance(existing_tags, str):
                    existing_tags = [existing_tags]
                new_tags = list(existing_tags)
                if slug not in new_tags:
                    new_tags.append(slug)
                if section_tag and section_tag not in new_tags:
                    new_tags.append(section_tag)
                # Handle existing neighbourhood field
                nb_field = post.metadata.get('neighbourhood', '')
                if nb_field:
                    nb_slug = nb_field.lower().replace(' ', '_').replace('-', '_')
                    if nb_slug not in new_tags:
                        new_tags.append(nb_slug)
                    del post.metadata['neighbourhood']
                # Infer type tags
                inferred_section = section_tag or slug
                for tag in infer_type_tags(post, inferred_section):
                    if tag not in new_tags:
                        new_tags.append(tag)
                # Drop category field
                if 'category' in post.metadata:
                    del post.metadata['category']
                post.metadata['tags'] = new_tags
                frontmatter.dump(post, poi_path)
                git(['mv', str(poi_path.relative_to(REPO)), str(dest.relative_to(REPO))])
                moved_files.append(dest)

    # Stage any modified section/neighbourhood .md files
    for subdir in subdirs:
        slug = subdir.name
        section_md = city_dir / f'{slug}.md'
        if section_md.exists():
            git(['add', str(section_md.relative_to(REPO))])

    # Delete now-empty subdirectories
    import shutil
    for subdir in subdirs:
        if not subdir.exists():
            continue  # Already removed (e.g. by git rm)
        remaining = list(subdir.rglob('*'))
        remaining_files = [f for f in remaining if f.is_file()]
        if not remaining_files:
            shutil.rmtree(subdir, ignore_errors=True)
            print(f'  Removed empty dir: {subdir.name}/')
        else:
            print(f'  WARNING: {subdir.name}/ still has files: {[f.name for f in remaining_files]}')

    # Run mark_done
    result = subprocess.run(
        ['python3', str(REPO / 'tools' / 'mark_done.py'), 'city_tag_migration', str(city_md)],
        capture_output=True, text=True, cwd=str(REPO)
    )
    if result.returncode != 0:
        print(f'  ERROR mark_done: {result.stderr}')
    else:
        print(f'  {result.stdout.strip()}')

    # Stage the city .md file
    git(['add', str(city_md.relative_to(REPO))])

    # Get city title for commit message
    post = frontmatter.load(city_md)
    city_title = post.metadata.get('title', city_slug.title())

    # Commit
    git(['commit', '-m', f'Tag migration: {city_title}'])
    print(f'  Committed: Tag migration: {city_title}')


def main() -> None:
    cities = sys.argv[1:] if len(sys.argv) > 1 else []
    if not cities:
        print('Usage: migrate_city_tags.py <city_path> [<city_path> ...]')
        sys.exit(1)

    for city_path in cities:
        try:
            migrate_city(city_path)
        except Exception as e:
            print(f'ERROR processing {city_path}: {e}')
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
