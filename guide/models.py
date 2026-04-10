"""
Filesystem-based content loading for World66.

Reads markdown files with YAML frontmatter from content/.
Uses the `type` field to classify pages:

  location      — continent, country, region, city
  section       — top-level navigable collection within a city (things_to_do, shopping, …)
  section_group — groups related nav pages in the sidebar (neighbourhoods, themes)
  neighbourhood — a district; appears under its section_group in the nav
  theme         — a cross-cutting theme (lgbtq, cold_war, …); appears under its section_group
  poi           — individual point of interest

All of section / section_group / neighbourhood / theme are "nav pages": they appear
in the city sidebar and each collects POIs by tag.  When a POI carries `tags: [de_pijp]`
and a page `de_pijp.md` exists with `type: neighbourhood`, that POI appears under De Pijp.

A nav page's query tag defaults to its slug; set `tag: <value>` in frontmatter to override.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import frontmatter
from django.conf import settings

CONTENT_DIR = Path(settings.BASE_DIR) / "content"

# Page types that participate in city navigation and collect POIs by tag.
NAV_TYPES = {"section", "section_group", "neighbourhood", "theme"}

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


def _load_md(path):
    """Load and parse a markdown file. Returns (meta, body) or None.

    Raises on invalid frontmatter — content is expected to be valid.
    Run `python3 tools/check_frontmatter.py` to find and fix broken files.
    """
    if not path.is_file():
        return None
    post = frontmatter.load(path)
    return post.metadata, post.content


@dataclass
class Page:
    """A single content page."""

    slug: str
    path: str       # relative path used in URLs
    title: str = ""
    page_type: str = "location"
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

    @property
    def category(self):
        return self.meta.get("category", "")

    @property
    def nav_tag(self):
        """The tag this nav page uses to collect its POIs. Defaults to slug."""
        return self.meta.get("tag", self.slug)

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
        """Sub-pages in this page's directory, grouped by type.

        Returns (nav_pages, locations, pois).  nav_pages covers all NAV_TYPES
        so the template can group them (sections at top, section_groups with
        their members nested, etc.).
        """
        dir_path = CONTENT_DIR / self.path
        if not dir_path.is_dir():
            return [], [], []

        nav_pages = []
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
                if page.page_type in NAV_TYPES:
                    nav_pages.append(page)
                elif page.page_type == "poi":
                    pois.append(page)
                else:
                    locations.append(page)

            elif entry.is_dir():
                child = load_page(self.path + "/" + entry.name)
                if child:
                    if child.page_type == "location":
                        locations.append(child)
                    elif child.page_type in NAV_TYPES:
                        nav_pages.append(child)

        return nav_pages, locations, pois

    def tagged_pois(self, _city_tag_index=None):
        """Return POIs tagged with this nav page's tag, found anywhere in the city.

        Also includes POIs in the legacy section subdirectory (files that
        predate the tag system and haven't been migrated yet).

        Pass _city_tag_index (from build_city_tag_index) to avoid repeated scans.
        """
        city_path = _find_city_path(self.path)
        if not city_path:
            return []
        tag = self.nav_tag
        by_tag = find_tagged_pois(city_path, tag, _city_tag_index=_city_tag_index)

        # Legacy: also scan the section's own subdirectory for untagged POIs
        legacy = self._legacy_dir_pois()
        seen = {p.path for p in by_tag}
        for p in legacy:
            if p.path not in seen:
                by_tag.append(p)

        return by_tag

    def _legacy_dir_pois(self):
        """POIs inside this page's own subdirectory (pre-tag content)."""
        dir_path = CONTENT_DIR / self.path
        if not dir_path.is_dir():
            # Also try sibling directory with same name as slug
            if "/" in self.path:
                dir_path = CONTENT_DIR / self.path.rsplit("/", 1)[0] / self.slug
        if not dir_path.is_dir():
            return []
        pois = []
        for entry in sorted(dir_path.iterdir()):
            if entry.is_file() and entry.suffix == ".md":
                page = _load_page_from_file(entry, self.path + "/" + entry.stem)
                if page and page.page_type == "poi":
                    pois.append(page)
        return pois

    # Keep old name for call sites not yet updated
    def pois(self):
        return self.tagged_pois()


def _find_city_path(path):
    """Return the path of the nearest ancestor page with type 'location'."""
    parts = path.split("/")
    for i in range(len(parts) - 1, 0, -1):
        candidate = "/".join(parts[:i])
        page = load_page(candidate)
        if page and page.page_type == "location":
            return candidate
    return None


def build_city_tag_index(city_path):
    """Scan all POI files under city_path once and return {tag: [Page, ...]}."""
    city_dir = CONTENT_DIR / city_path
    if not city_dir.is_dir():
        return {}
    index = {}
    seen = set()
    for md_file in sorted(city_dir.rglob("*.md")):
        result = _load_md(md_file)
        if not result:
            continue
        meta, _ = result
        if meta.get("type") != "poi":
            continue
        raw_tags = meta.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [t.strip() for t in raw_tags.split(",")]
        if not raw_tags:
            continue
        rel = md_file.relative_to(CONTENT_DIR)
        parts = list(rel.parts)
        stem = parts[-1][:-3]
        url_path = "/".join(parts[:-1] + [stem])
        if url_path in seen:
            continue
        seen.add(url_path)
        page = _load_page_from_file(md_file, url_path)
        if page:
            for t in raw_tags:
                index.setdefault(t, []).append(page)
    return index


def find_tagged_pois(city_path, tag, _city_tag_index=None):
    """Return POIs under city_path tagged with tag.

    Pass _city_tag_index (from build_city_tag_index) to avoid repeated scans.
    """
    if _city_tag_index is None:
        _city_tag_index = build_city_tag_index(city_path)
    return list(_city_tag_index.get(tag, []))


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
    """Load a page by its URL path."""
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


def resolve_tag_route(path):
    """Resolve a virtual tag-based URL: city/nav-slug/poi-slug.

    Returns (poi_page, nav_page) or (None, None).

    When a POI tagged 'de_pijp' is accessed via /amsterdam/de_pijp/albert_cuypmarkt,
    the file may physically live at /amsterdam/shopping/albert_cuypmarkt.md.
    This function finds it by tag lookup.
    """
    parts = path.split("/")
    if len(parts) < 2:
        return None, None

    poi_slug = parts[-1]

    # Try each possible split: city = parts[:i], nav = parts[i], poi = parts[i+1:]
    # We only support one nav-slug level (not nested like neighbourhoods/de_pijp/poi)
    # Nested case (section_group/nav/poi) is handled by trying i and i-1.
    for city_len in range(len(parts) - 2, 0, -1):
        city_path = "/".join(parts[:city_len])
        nav_slug = parts[city_len]

        city_page = load_page(city_path)
        if not city_page or city_page.page_type != "location":
            continue

        nav_page = load_page(city_path + "/" + nav_slug)
        if not nav_page or nav_page.page_type not in NAV_TYPES:
            continue

        # Find a POI in this city tagged with the nav page's tag
        tag = nav_page.nav_tag
        for poi in find_tagged_pois(city_path, tag):
            if poi.slug == poi_slug:
                return poi, nav_page

        break  # found valid city/nav, but no matching poi

    return None, None


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
        rel = md_file.relative_to(CONTENT_DIR)
        parts = list(rel.parts)
        if parts[-1].endswith(".md"):
            stem = parts[-1][:-3]
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
