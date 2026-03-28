"""
Import extracted World66 content (markdown files) into the database.

Usage: python manage.py import_content /path/to/restore/content
"""

import os
import re

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from guide.models import Location, Section

# Map path prefixes to nice continent names
CONTINENT_NAMES = {
    "africa": "Africa",
    "antarctica": "Antarctica",
    "asia": "Asia",
    "australiaandpacific": "Australia & Pacific",
    "centralamericathecaribbean": "Central America & Caribbean",
    "europe": "Europe",
    "northamerica": "North America",
    "southamerica": "South America",
    "world": "World",
}

# Known section slugs — if the last path component matches, it's a section
SECTION_SLUGS = {
    "sights", "eating_out", "getting_there", "getting_around",
    "practical_informat", "things_to_do", "day_trips", "shopping",
    "beaches", "museums", "nightlife_and_ente", "nightlife",
    "bars_and_cafes", "festivals", "when_to_go", "top_5_must_dos",
    "activities", "books", "people", "budget_travel_idea",
    "family_travel_idea", "tours_and_excursio", "travel_guide",
    "7_day_itinerary",
}

SECTION_DISPLAY = {
    "sights": "Sights",
    "eating_out": "Eating Out",
    "getting_there": "Getting There",
    "getting_around": "Getting Around",
    "practical_informat": "Practical Information",
    "things_to_do": "Things to Do",
    "day_trips": "Day Trips",
    "shopping": "Shopping",
    "beaches": "Beaches",
    "museums": "Museums",
    "nightlife_and_ente": "Nightlife & Entertainment",
    "nightlife": "Nightlife",
    "bars_and_cafes": "Bars & Cafes",
    "festivals": "Festivals",
    "when_to_go": "When to Go",
    "top_5_must_dos": "Top 5 Must Do's",
    "activities": "Activities",
    "books": "Books",
    "people": "People",
    "budget_travel_idea": "Budget Travel Ideas",
    "family_travel_idea": "Family Travel Ideas",
    "tours_and_excursio": "Tours & Excursions",
    "travel_guide": "Travel Guide",
    "7_day_itinerary": "7-Day Itinerary",
}


def slug_to_name(slug):
    """Convert a URL slug to a display name."""
    return slug.replace("_", " ").replace("-", " ").title()


def parse_markdown(filepath):
    """Read a markdown file and extract title, body, and frontmatter properties."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse frontmatter
    properties = {}
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            fm = content[3:end].strip()
            for line in fm.split("\n"):
                if ": " in line:
                    key, val = line.split(": ", 1)
                    val = val.strip().strip('"')
                    properties[key.strip()] = val
            content = content[end + 3:].strip()

    # Extract title from first # heading
    title = properties.pop("title", "")
    body = content
    m = re.match(r"^# (.+)\n", content)
    if m:
        if not title:
            title = m.group(1).strip()
        body = content[m.end():]

    # Strip breadcrumb line
    body = re.sub(r"^\*[^*]+\*\s*\n*", "", body)

    body = body.strip()
    return title, body, properties


class Command(BaseCommand):
    help = "Import extracted World66 markdown content into the database"

    def add_arguments(self, parser):
        parser.add_argument("content_dir", help="Path to the content/ directory")
        parser.add_argument("--clear", action="store_true",
                            help="Clear existing data before import")

    def handle(self, *args, **options):
        content_dir = options["content_dir"]

        if not os.path.isdir(content_dir):
            self.stderr.write(f"Not a directory: {content_dir}")
            return

        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            Section.objects.all().delete()
            Location.objects.all().delete()

        # Collect all markdown files
        md_files = []
        for root, dirs, files in os.walk(content_dir):
            for f in files:
                if f.endswith(".md"):
                    md_files.append(os.path.join(root, f))

        self.stdout.write(f"Found {len(md_files)} markdown files")

        # Sort so parent directories come before children
        md_files.sort(key=lambda p: os.path.relpath(p, content_dir))

        # Cache for location lookups
        location_cache = {}
        locations_created = 0
        sections_created = 0

        for filepath in md_files:
            rel_path = os.path.relpath(filepath, content_dir)
            # Remove .md extension
            rel_path = rel_path[:-3]
            parts = rel_path.split(os.sep)

            if not parts:
                continue

            title, body, properties = parse_markdown(filepath)

            # Determine if last segment is a section
            last_segment = parts[-1]
            is_section = last_segment in SECTION_SLUGS and len(parts) >= 2

            if is_section:
                loc_parts = parts[:-1]
                section_slug = last_segment
            else:
                loc_parts = parts
                section_slug = None

            # Ensure all ancestor locations exist
            for i in range(len(loc_parts)):
                loc_path = "/".join(loc_parts[:i + 1])

                if loc_path in location_cache:
                    continue

                slug = loc_parts[i]
                parent_path = "/".join(loc_parts[:i]) if i > 0 else None
                parent = location_cache.get(parent_path)

                # Determine name
                if i == 0 and slug in CONTINENT_NAMES:
                    name = CONTINENT_NAMES[slug]
                else:
                    name = slug_to_name(slug)

                loc, created = Location.objects.get_or_create(
                    path=loc_path,
                    defaults={
                        "name": name,
                        "slug": slug,
                        "parent": parent,
                        "depth": i,
                    },
                )
                location_cache[loc_path] = loc
                if created:
                    locations_created += 1

            # Now store the content
            loc_path = "/".join(loc_parts)
            location = location_cache[loc_path]

            if is_section:
                # It's a section
                section_title = title or SECTION_DISPLAY.get(section_slug, slug_to_name(section_slug))
                section, created = Section.objects.update_or_create(
                    location=location,
                    slug=section_slug,
                    defaults={
                        "section_type": section_slug,
                        "title": section_title,
                        "body": body,
                        "properties": properties,
                    },
                )
                if created:
                    sections_created += 1
            else:
                # It's a location page — update the location body
                if not location.body and body:
                    location.body = body
                    if title and title != location.name:
                        location.name = title
                    location.save()

            if (locations_created + sections_created) % 500 == 0:
                self.stdout.write(
                    f"  {locations_created} locations, {sections_created} sections..."
                )

        self.stdout.write(self.style.SUCCESS(
            f"Done! {locations_created} locations, {sections_created} sections imported."
        ))
