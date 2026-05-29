#!/usr/bin/env python3
"""Migrate POIs from section/neighbourhood subdirectories to city root with tags."""

import os
import sys
import subprocess
from pathlib import Path
import frontmatter


def get_subdirs(city_path: Path) -> list[Path]:
    """Return subdirectories of city_path."""
    return [d for d in city_path.iterdir() if d.is_dir()]


def get_poi_files(subdir: Path) -> list[Path]:
    """Return .md files in a subdirectory."""
    return list(subdir.glob('*.md'))


def ensure_type(page_path: Path, type_val: str) -> None:
    """Ensure the section/neighbourhood page has a type field."""
    if not page_path.exists():
        return
    page = frontmatter.load(page_path)
    if not page.get('type'):
        page['type'] = type_val
        with open(page_path, 'wb') as f:
            frontmatter.dump(page, f)
        print(f'  Set type={type_val} on {page_path.name}')


def add_tag(page: frontmatter.Post, tag: str) -> None:
    """Add a tag to a page if not already present."""
    tags = list(page.get('tags', []) or [])
    if tag not in tags:
        tags.append(tag)
    page['tags'] = tags


def migrate_city(city_rel: str, base: Path) -> bool:
    """Migrate a single city. Returns True if any changes were made."""
    city_path = base / city_rel
    city_md = city_path.with_suffix('.md')
    if not city_path.exists():
        print(f'SKIP (no dir): {city_rel}')
        return False

    subdirs = get_subdirs(city_path)
    if not subdirs:
        print(f'SKIP (no subdirs): {city_rel}')
        return False

    city_name_parts = city_rel.split('/')
    city_slug = city_name_parts[-1]
    print(f'\nProcessing: {city_rel}')

    any_changes = False

    for subdir in sorted(subdirs):
        section_slug = subdir.name
        poi_files = get_poi_files(subdir)

        if not poi_files:
            print(f'  Subdir {section_slug}: empty, removing')
            subdir.rmdir()
            continue

        # Determine type for section page
        section_md = city_path / f'{section_slug}.md'
        if section_md.exists():
            sec_page = frontmatter.load(section_md)
            sec_type = sec_page.get('type', '')
            if not sec_type:
                sec_type = 'section'
                sec_page['type'] = sec_type
                with open(section_md, 'wb') as f:
                    frontmatter.dump(sec_page, f)
                print(f'  Set type=section on {section_slug}.md')
        else:
            sec_type = 'section'

        print(f'  Migrating {len(poi_files)} POIs from {section_slug}/')

        for poi_path in sorted(poi_files):
            # Read POI
            page = frontmatter.load(poi_path)

            # Add section tag
            add_tag(page, section_slug)

            # Check for neighbourhood field and add as tag too
            neighbourhood = page.get('neighbourhood', '')
            if neighbourhood:
                # Convert neighbourhood name to slug
                nb_slug = neighbourhood.lower().replace(' ', '_').replace('-', '_')
                add_tag(page, nb_slug)
                del page['neighbourhood']

            # Determine destination path
            dest_path = city_path / poi_path.name

            # Handle name collision
            if dest_path.exists():
                stem = poi_path.stem
                dest_path = city_path / f'{stem}_{section_slug}.md'
                print(f'  Name collision: renaming to {dest_path.name}')

            # Write back to original location first
            with open(poi_path, 'wb') as f:
                frontmatter.dump(page, f)

            # Git mv to city root
            result = subprocess.run(
                ['git', 'mv', str(poi_path), str(dest_path)],
                cwd=str(base),
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f'  ERROR git mv {poi_path.name}: {result.stderr}')
            else:
                print(f'  Moved {poi_path.name} -> {dest_path.name}')

            any_changes = True

        # Check if subdir is now empty
        remaining = list(subdir.glob('*'))
        if not remaining:
            subdir.rmdir()
            print(f'  Removed empty dir: {section_slug}/')
        else:
            print(f'  Subdir {section_slug}/ still has: {[f.name for f in remaining]}')

    return any_changes


def main() -> None:
    base = Path('/Users/hp/proj/world66/content')
    cities = [
        'europe/norway/trondheim',
        'europe/poland/gdansk',
        'europe/portugal/theazores/so_miguel/ponta_delgada',
        'europe/slovenia/ljubljana',
        'europe/spain/andalucia/marbella',
        'europe/spain/canaryislands/grancanaria/las_palmas',
        'europe/spain/galicia/lacoruna',
        'europe/sweden/gothenburg',
        'europe/unitedkingdom/england/birmingham_and_wes/coventry',
        'northamerica/mexico/puertovallarta',
        'northamerica/thecaribbean/anguilla',
        'northamerica/unitedstates/california/losangeles/pasadena',
        'northamerica/unitedstates/nevada/reno',
        'southamerica/peru/cuzco',
        'africa/egypt/al_qahera__cairo',
        'africa/senegal/saintlouis',
        'africa/uganda/kampala',
        'asia/india/andhrapradesh/visakhapatnam',
        'asia/india/rajasthan/jaipur',
        'asia/india/rajasthan/udaipur',
        'asia/indonesia/batam',
        'asia/japan/tokyo/roppongi',
        'asia/nepal/kathmandu',
        'asia/thailand/ayutthaya',
        'asia/thailand/krabi',
        'asia/thailand/nonthaburi_2',
        'asia/vietnam/hanoi',
        'australiaandpacific/australia/queensland/brisbane',
        'australiaandpacific/newcaledonia/lifou',
        'australiaandpacific/newzealand/south_island/otago/dunedin',
        'europe/armenia/yerevan',
        'europe/belgium/ghent',
        'europe/france/east/alsace/strasbourg',
        'europe/france/midi/provence/avignon',
        'europe/germany/northrhinewestphalia/cologne',
        'europe/germany/saxonyanhalt/halle',
        'europe/italy/emiliaromagna/bologna',
        'europe/malta/valletta',
        'europe/montenegro/kotor',
        'europe/netherlands/breda',
        'europe/netherlands/ede',
        'northamerica/canada/ontario/thunder_bay',
        'northamerica/unitedstates/alabama/birmingham',
        'northamerica/unitedstates/california/centralcoast/santabarbara',
        'northamerica/unitedstates/california/inlandempire/redlands',
        'northamerica/unitedstates/connecticut/hartford',
        'northamerica/unitedstates/georgia/atlanta',
        'northamerica/unitedstates/missouri/kansascity',
        'northamerica/unitedstates/oklahoma/oklahomacity',
        'northamerica/unitedstates/tennessee/chattanooga',
    ]

    processed = []
    skipped = []

    for city_rel in cities:
        changed = migrate_city(city_rel, base)
        if changed:
            processed.append(city_rel)
        else:
            skipped.append(city_rel)

    print(f'\n\nSummary:')
    print(f'Processed ({len(processed)}): {processed}')
    print(f'Skipped ({len(skipped)}): {skipped}')


if __name__ == '__main__':
    main()
