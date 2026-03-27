import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from django.conf import settings

CONTENT_DIR = Path(settings.BASE_DIR) / "restore" / "content"

SECTION_TYPES = {
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


def _parse_frontmatter(text):
    """Parse YAML frontmatter and body from a markdown file."""
    if text.startswith("---"):
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if match:
            try:
                meta = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                meta = {}
            return meta, match.group(2)
    return {}, text


@dataclass
class Location:
    name: str
    slug: str
    path: str
    body: str = ""
    meta: dict = field(default_factory=dict)

    def get_absolute_url(self):
        return f"/{self.path}"

    def breadcrumbs(self):
        crumbs = []
        parts = self.path.split("/")
        for i in range(len(parts)):
            ancestor_path = "/".join(parts[: i + 1])
            ancestor = load_location(ancestor_path)
            if ancestor:
                crumbs.append((ancestor.name, ancestor.path))
            else:
                crumbs.append((parts[i].replace("_", " ").title(), ancestor_path))
        return crumbs

    def children(self):
        dir_path = CONTENT_DIR / self.path
        if not dir_path.is_dir():
            return []
        children = []
        for entry in sorted(dir_path.iterdir()):
            if entry.is_dir():
                child = load_location(self.path + "/" + entry.name)
                if child:
                    children.append(child)
        return children

    def sections(self):
        dir_path = CONTENT_DIR / self.path
        if not dir_path.is_dir():
            return []
        sections = []
        location_slug = self.path.rsplit("/", 1)[-1]
        for entry in sorted(dir_path.iterdir()):
            if entry.is_file() and entry.suffix == ".md" and entry.stem != location_slug:
                section = load_section(self.path, entry.stem)
                if section:
                    sections.append(section)
        return sections


@dataclass
class Section:
    slug: str
    title: str
    section_type: str
    body: str = ""
    location_path: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def properties(self):
        return {k: v for k, v in self.meta.items() if k != "title"}

    @property
    def display_name(self):
        return SECTION_TYPES.get(self.section_type, self.title)

    def get_absolute_url(self):
        return f"/{self.location_path}/{self.slug}"


def load_location(path):
    """Load a location from the filesystem. Returns None if not found."""
    slug = path.rsplit("/", 1)[-1] if "/" in path else path
    # The location's own markdown file lives inside its directory
    md_file = CONTENT_DIR / path / f"{slug}.md"
    # Some continents have the md file next to the directory
    md_file_alt = CONTENT_DIR / f"{path}.md"

    for f in [md_file, md_file_alt]:
        if f.is_file():
            text = f.read_text(encoding="utf-8", errors="replace")
            meta, body = _parse_frontmatter(text)
            name = meta.get("title", slug.replace("_", " ").title())
            return Location(name=name, slug=slug, path=path, body=body, meta=meta)

    # Directory exists but no matching markdown file — still valid as a location
    dir_path = CONTENT_DIR / path
    if dir_path.is_dir():
        return Location(
            name=slug.replace("_", " ").title(), slug=slug, path=path,
        )
    return None


def load_section(location_path, section_slug):
    """Load a section markdown file for a location."""
    md_file = CONTENT_DIR / location_path / f"{section_slug}.md"
    if not md_file.is_file():
        return None
    text = md_file.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(text)
    title = meta.get("title", section_slug.replace("_", " ").title())
    section_type = section_slug
    return Section(
        slug=section_slug,
        title=title,
        section_type=section_type,
        body=body,
        location_path=location_path,
        meta=meta,
    )


def load_continents():
    """Load top-level locations (continents)."""
    continents = []
    for entry in sorted(CONTENT_DIR.iterdir()):
        if entry.is_dir():
            loc = load_location(entry.name)
            if loc:
                continents.append(loc)
        elif entry.is_file() and entry.suffix == ".md":
            # Continent md file without a directory (e.g. southamerica.md)
            name = entry.stem
            if not (CONTENT_DIR / name).is_dir():
                continue  # only if there's a matching directory
    return continents
