"""
Filesystem-based content loading for World66.

Reads markdown files with YAML frontmatter from content/.
Uses the `type` field (location, section, poi) to classify pages.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from django.conf import settings

CONTENT_DIR = Path(settings.BASE_DIR) / "content"

SECTION_DISPLAY_NAMES = {
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


def _load_md(path):
    """Load and parse a markdown file. Returns (meta, body) or None."""
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    return _parse_frontmatter(text)


@dataclass
class Page:
    """A single content page — location, section, or POI."""

    slug: str
    path: str       # relative path used in URLs
    title: str = ""
    page_type: str = "location"  # location, section, poi
    body: str = ""
    meta: dict = field(default_factory=dict)

    def get_absolute_url(self):
        return f"/{self.path}"

    @property
    def display_name(self):
        if self.page_type == "section":
            return SECTION_DISPLAY_NAMES.get(self.slug, self.title)
        return self.title

    DISPLAY_PROPERTIES = {
        "address": "Address",
        "phone": "Phone",
        "url": "Website",
        "email": "Email",
        "opening_hours": "Opening Hours",
        "closing_time": "Closing Time",
        "price": "Price",
        "admission": "Admission",
        "isbn": "ISBN",
        "author": "Author",
        "connections": "Connections",
        "getting_there": "Getting There",
        "accessibility": "Accessibility",
        "zipcode": "Zip Code",
        "price_per_night": "Price/Night",
    }

    @property
    def properties(self):
        return {
            self.DISPLAY_PROPERTIES[k]: v
            for k, v in self.meta.items()
            if k in self.DISPLAY_PROPERTIES
        }

    def breadcrumbs(self):
        crumbs = []
        parts = self.path.split("/")
        for i in range(len(parts)):
            ancestor_path = "/".join(parts[: i + 1])
            ancestor = load_page(ancestor_path)
            if ancestor:
                crumbs.append((ancestor.title, ancestor.path))
            else:
                crumbs.append((parts[i].replace("_", " ").title(), ancestor_path))
        return crumbs

    def children(self):
        """Sub-pages in this page's directory, grouped by type."""
        dir_path = CONTENT_DIR / self.path
        if not dir_path.is_dir():
            return [], [], []

        sections = []
        locations = []
        pois = []

        for entry in sorted(dir_path.iterdir()):
            if entry.is_file() and entry.suffix == ".md":
                # Skip the location's own .md file (slug matches directory)
                if entry.stem == self.slug:
                    continue
                page = _load_page_from_file(entry, self.path + "/" + entry.stem)
                if not page:
                    continue
                if page.page_type == "section":
                    sections.append(page)
                elif page.page_type == "poi":
                    pois.append(page)
                else:
                    locations.append(page)

            elif entry.is_dir():
                # A section/POI directory only contains .md files.
                # A sub-location directory contains other directories too.
                has_subdirs = any(f.is_dir() for f in entry.iterdir())
                if not has_subdirs:
                    # Pure .md directory — check if it's POIs
                    sample_md = next(
                        (f for f in entry.iterdir() if f.suffix == ".md"), None
                    )
                    if sample_md:
                        text = sample_md.read_text(encoding="utf-8", errors="replace")
                        if "type: poi" in text:
                            continue
                child = load_page(self.path + "/" + entry.name)
                if child:
                    locations.append(child)

        return sections, locations, pois

    def pois(self):
        """POIs inside this section's directory (for section pages)."""
        dir_path = CONTENT_DIR / self.path
        if not dir_path.is_dir():
            # Section slug might be a file, check for matching directory
            parts = self.path.rsplit("/", 1)
            if len(parts) == 2:
                dir_path = CONTENT_DIR / parts[0] / self.slug
        if not dir_path.is_dir():
            return []

        pois = []
        for entry in sorted(dir_path.iterdir()):
            if entry.is_file() and entry.suffix == ".md":
                poi_path = self.path + "/" + entry.stem
                page = _load_page_from_file(entry, poi_path)
                if page:
                    pois.append(page)
        return pois


def _load_page_from_file(file_path, url_path):
    """Load a Page from a specific .md file."""
    result = _load_md(file_path)
    if not result:
        return None
    meta, body = result
    slug = file_path.stem
    title = meta.get("title", slug.replace("_", " ").title())
    page_type = meta.get("type", "location")
    return Page(
        slug=slug, path=url_path, title=title,
        page_type=page_type, body=body, meta=meta,
    )


def load_page(path):
    """Load a page by its URL path. Tries location .md files first."""
    slug = path.rsplit("/", 1)[-1] if "/" in path else path

    # Location's own .md file lives inside its directory
    for md_file in [
        CONTENT_DIR / path / f"{slug}.md",
        CONTENT_DIR / f"{path}.md",
    ]:
        if md_file.is_file():
            return _load_page_from_file(md_file, path)

    # Directory exists but no .md file — still valid as a location
    if (CONTENT_DIR / path).is_dir():
        return Page(
            slug=slug, path=path,
            title=slug.replace("_", " ").title(),
            page_type="location",
        )
    return None


def load_continents():
    """Load top-level locations with their children (countries)."""
    continents = []
    for entry in sorted(CONTENT_DIR.iterdir()):
        if entry.is_dir():
            loc = load_page(entry.name)
            if loc:
                _, locations, _ = loc.children()
                continents.append((loc, locations))
    return continents
