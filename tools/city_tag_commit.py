#!/usr/bin/env python3
"""Run mark_done and commit for each city after tag migration."""

import subprocess
import sys
from pathlib import Path


CITIES = [
    ('europe/norway/trondheim', 'Trondheim'),
    ('europe/poland/gdansk', 'Gdansk'),
    ('europe/portugal/theazores/so_miguel/ponta_delgada', 'Ponta Delgada'),
    ('europe/slovenia/ljubljana', 'Ljubljana'),
    ('europe/spain/andalucia/marbella', 'Marbella'),
    ('europe/spain/canaryislands/grancanaria/las_palmas', 'Las Palmas'),
    ('europe/spain/galicia/lacoruna', 'La Coruna'),
    ('europe/sweden/gothenburg', 'Gothenburg'),
    ('europe/unitedkingdom/england/birmingham_and_wes/coventry', 'Coventry'),
    ('northamerica/mexico/puertovallarta', 'Puerto Vallarta'),
    ('northamerica/thecaribbean/anguilla', 'Anguilla'),
    ('northamerica/unitedstates/california/losangeles/pasadena', 'Pasadena'),
    ('northamerica/unitedstates/nevada/reno', 'Reno'),
    ('southamerica/peru/cuzco', 'Cuzco'),
    ('africa/egypt/al_qahera__cairo', 'Cairo'),
    ('africa/senegal/saintlouis', 'Saint-Louis'),
    ('africa/uganda/kampala', 'Kampala'),
    ('asia/india/andhrapradesh/visakhapatnam', 'Visakhapatnam'),
    ('asia/india/rajasthan/jaipur', 'Jaipur'),
    ('asia/india/rajasthan/udaipur', 'Udaipur'),
    ('asia/indonesia/batam', 'Batam'),
    ('asia/japan/tokyo/roppongi', 'Roppongi'),
    ('asia/nepal/kathmandu', 'Kathmandu'),
    ('asia/thailand/ayutthaya', 'Ayutthaya'),
    ('asia/thailand/krabi', 'Krabi'),
    ('asia/thailand/nonthaburi_2', 'Nonthaburi'),
    ('asia/vietnam/hanoi', 'Hanoi'),
    ('australiaandpacific/australia/queensland/brisbane', 'Brisbane'),
    ('australiaandpacific/newcaledonia/lifou', 'Lifou'),
    ('australiaandpacific/newzealand/south_island/otago/dunedin', 'Dunedin'),
    ('europe/armenia/yerevan', 'Yerevan'),
    ('europe/belgium/ghent', 'Ghent'),
    ('europe/france/east/alsace/strasbourg', 'Strasbourg'),
    ('europe/france/midi/provence/avignon', 'Avignon'),
    ('europe/germany/northrhinewestphalia/cologne', 'Cologne'),
    ('europe/germany/saxonyanhalt/halle', 'Halle'),
    ('europe/italy/emiliaromagna/bologna', 'Bologna'),
    ('europe/malta/valletta', 'Valletta'),
    ('europe/montenegro/kotor', 'Kotor'),
    ('europe/netherlands/breda', 'Breda'),
    ('europe/netherlands/ede', 'Ede'),
    ('northamerica/canada/ontario/thunder_bay', 'Thunder Bay'),
    ('northamerica/unitedstates/alabama/birmingham', 'Birmingham'),
    ('northamerica/unitedstates/california/centralcoast/santabarbara', 'Santa Barbara'),
    ('northamerica/unitedstates/california/inlandempire/redlands', 'Redlands'),
    ('northamerica/unitedstates/connecticut/hartford', 'Hartford'),
    ('northamerica/unitedstates/georgia/atlanta', 'Atlanta'),
    ('northamerica/unitedstates/missouri/kansascity', 'Kansas City'),
    ('northamerica/unitedstates/oklahoma/oklahomacity', 'Oklahoma City'),
    ('northamerica/unitedstates/tennessee/chattanooga', 'Chattanooga'),
]


def run(cmd: list[str], cwd: str = '/Users/hp/proj/world66') -> int:
    """Run a command, print output, return exit code."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def main() -> None:
    base = Path('/Users/hp/proj/world66')

    for city_rel, city_name in CITIES:
        city_path = base / 'content' / city_rel
        city_md = (base / 'content' / city_rel).with_suffix('.md')

        print(f'\n=== {city_name} ===')

        # Run mark_done
        result = subprocess.run(
            ['python3', 'tools/mark_done.py', 'city_tag_migration', str(city_md)],
            cwd=str(base), capture_output=True, text=True
        )
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f'mark_done failed: {result.stderr}', file=sys.stderr)

        # Stage all changes
        rc = run(['git', 'add', '-A'])
        if rc != 0:
            print(f'git add failed for {city_name}')
            continue

        # Commit
        msg = f'Tag migration: {city_name}'
        rc = run(['git', 'commit', '-m', msg])
        if rc != 0:
            print(f'git commit failed for {city_name}')

    print('\nAll done!')


if __name__ == '__main__':
    main()
