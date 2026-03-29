"""
Filesystem-based content loading for World66.

Reads markdown files with YAML frontmatter from content/.
Uses the `type` field (location, section, poi) to classify pages.
The frontmatter title is the source of truth — no runtime name mapping.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from django.conf import settings

CONTENT_DIR = Path(settings.BASE_DIR) / "content"

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


def _get_page_type(file_path):
    """Get the page type from a markdown file's frontmatter."""
    result = _load_md(file_path)
    if not result:
        return None
    meta, _ = result
    return meta.get("type", "location")


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
    def properties(self):
        return {
            DISPLAY_PROPERTIES[k]: v
            for k, v in self.meta.items()
            if k in DISPLAY_PROPERTIES
        }

    @property
    def tags(self):
        raw = self.meta.get("tags", [])
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(",") if t.strip()]
        return []

    def breadcrumbs(self):
        crumbs = []
        parts = self.path.split("/")
        for i in range(len(parts)):
            ancestor_path = "/".join(parts[: i + 1])
            ancestor = load_page(ancestor_path)
            if ancestor:
                crumbs.append((ancestor.title, ancestor.path))
            else:
                crumbs.append((parts[i], ancestor_path))
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
                if entry.stem == self.slug:
                    continue
                if (dir_path / entry.stem).is_dir():
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
                child = load_page(self.path + "/" + entry.name)
                if child and child.page_type == "location":
                    locations.append(child)

        return sections, locations, pois

    def pois(self):
        """POIs inside this section's directory (for section pages)."""
        dir_path = CONTENT_DIR / self.path
        if not dir_path.is_dir():
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
    title = meta.get("title", slug)
    page_type = meta.get("type", "location")
    return Page(
        slug=slug, path=url_path, title=title,
        page_type=page_type, body=body, meta=meta,
    )


def load_page(path):
    """Load a page by its URL path. Tries location .md files, then
    falls back to section/poi .md inside a parent directory."""
    slug = path.rsplit("/", 1)[-1] if "/" in path else path

    for md_file in [
        CONTENT_DIR / path / f"{slug}.md",
        CONTENT_DIR / f"{path}.md",
    ]:
        if md_file.is_file():
            return _load_page_from_file(md_file, path)

    if "/" in path:
        parent_path, slug = path.rsplit("/", 1)
        md_file = CONTENT_DIR / parent_path / f"{slug}.md"
        if md_file.is_file():
            return _load_page_from_file(md_file, path)

    return None


@lru_cache(maxsize=1)
def load_search_index():
    """Return a list of (title_lower, title, url_path) for all content pages."""
    entries = []
    for md_file in sorted(CONTENT_DIR.rglob("*.md")):
        result = _load_md(md_file)
        if not result:
            continue
        meta, _ = result
        title = meta.get("title", "")
        if not title:
            continue
        rel = md_file.relative_to(CONTENT_DIR)
        parts = list(rel.parts)
        stem = parts[-1][:-3]
        if len(parts) >= 2 and stem == parts[-2]:
            url_path = "/".join(parts[:-1])
        else:
            url_path = "/".join(parts[:-1] + [stem]) if len(parts) > 1 else stem
        entries.append((title.lower(), title, url_path, meta.get("type", "location")))
    return entries


@lru_cache(maxsize=1)
def load_tag_index():
    """Scan all content files and return a dict mapping tag -> list of Pages."""
    index = {}
    for md_file in sorted(CONTENT_DIR.rglob("*.md")):
        result = _load_md(md_file)
        if not result:
            continue
        meta, body = result
        raw_tags = meta.get("tags", [])
        if not raw_tags:
            continue
        if isinstance(raw_tags, str):
            raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        if not isinstance(raw_tags, list):
            continue
        # Derive the URL path from the file path relative to CONTENT_DIR
        rel = md_file.relative_to(CONTENT_DIR)
        parts = list(rel.parts)
        if parts[-1].endswith(".md"):
            stem = parts[-1][:-3]
            # If the stem matches the parent directory name, it's the location file
            if len(parts) >= 2 and stem == parts[-2]:
                url_path = "/".join(parts[:-1])
            else:
                url_path = "/".join(parts[:-1] + [stem]) if len(parts) > 1 else stem
        else:
            url_path = "/".join(parts)
        page = _load_page_from_file(md_file, url_path)
        if not page:
            continue
        for tag in raw_tags:
            index.setdefault(tag, []).append(page)
    return index


@lru_cache(maxsize=1)
def load_continents():
    """Load top-level locations with their children (countries)."""
    continents = []
    CONTINENT_SLUGS = {
        "africa", "antarctica", "asia", "australiaandpacific",
        "europe", "northamerica", "southamerica",
    }
    for entry in sorted(CONTENT_DIR.iterdir()):
        if entry.is_dir() and entry.name in CONTINENT_SLUGS:
            loc = load_page(entry.name)
            if loc:
                _, locations, _ = loc.children()
                continents.append((loc, locations))
    return continents
