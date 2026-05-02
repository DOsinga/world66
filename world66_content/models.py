"""
Filesystem-based content loading for World66.

Reads markdown files with YAML frontmatter from content/.
Uses the `type` field to classify pages:

  location      — continent, country, region, city
  section       — top-level navigable collection within a city (things_to_do, shopping, …)
  theme         — a cross-cutting theme (lgbtq, cold_war, …)
  poi           — individual point of interest; use `category` to sub-type:
                    walk        — city walk with route + waypoints
                    vibe        — half-day itinerary; tag with `vibes` to show on city page
                    neighbourhood — district; tag with `neighbourhoods` to show on city page

Section and theme are "nav pages": they appear in the city sidebar and collect POIs by tag.
A nav page's query tag defaults to its slug; set `tag: <value>` in frontmatter to override.

Configuration
-------------
Set WORLD66_CONTENT_DIR in your Django settings to the absolute path of the content/
directory. Both the main world66 project and any separate plans deployment need this.

    WORLD66_CONTENT_DIR = BASE_DIR / "content"
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import frontmatter
from django.conf import settings

# Page types that participate in city navigation and collect POIs by tag.
NAV_TYPES = {"section", "theme"}

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


def _content_dir():
    return Path(settings.WORLD66_CONTENT_DIR)


# Module-level alias for convenience — evaluated lazily via property-like access
# is not possible on a module, so callers that need the path use _content_dir().
# For backwards-compat with code that imported CONTENT_DIR directly, we expose
# a property-like object that resolves on first access.
class _LazyContentDir:
    """Proxy that behaves like a Path but resolves settings lazily."""
    def __getattr__(self, name):
        return getattr(_content_dir(), name)
    def __truediv__(self, other):
        return _content_dir() / other
    def __rtruediv__(self, other):
        return Path(other) / _content_dir()
    def __str__(self):
        return str(_content_dir())
    def __repr__(self):
        return repr(_content_dir())
    def __fspath__(self):
        return str(_content_dir())


CONTENT_DIR = _LazyContentDir()


def _load_md(path):
    """Load and parse a markdown file. Returns (meta, body) or None."""
    if not path.is_file():
        return None
    post = frontmatter.load(path)
    return post.metadata, post.content


@dataclass
class Page:
    """A single content page."""

    slug: str
    path: str
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

    _CATEGORY_TAGS = {"sight", "museum", "architecture", "neighbourhood", "restaurant", "bar", "market"}

    @property
    def category(self):
        explicit = self.meta.get("category", "")
        if explicit:
            return explicit
        for t in self.tags:
            if t in self._CATEGORY_TAGS:
                return t.replace("_", " ").title()
        return ""

    @property
    def nav_tag(self):
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
        dir_path = _content_dir() / self.path
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
                elif page.meta.get("type") == "poi":
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
        city_path = _find_city_path(self.path)
        if not city_path:
            return []
        tag = self.nav_tag
        by_tag = find_tagged_pois(city_path, tag, _city_tag_index=_city_tag_index)
        legacy = self._legacy_dir_pois()
        seen = {p.path for p in by_tag}
        for p in legacy:
            if p.path not in seen:
                by_tag.append(p)
        return by_tag

    def _legacy_dir_pois(self):
        dir_path = _content_dir() / self.path
        if not dir_path.is_dir():
            if "/" in self.path:
                dir_path = _content_dir() / self.path.rsplit("/", 1)[0] / self.slug
        if not dir_path.is_dir():
            return []
        pois = []
        for entry in sorted(dir_path.iterdir()):
            if entry.is_file() and entry.suffix == ".md":
                page = _load_page_from_file(entry, self.path + "/" + entry.stem)
                if page and page.page_type == "poi":
                    pois.append(page)
        return pois

    def pois(self):
        return self.tagged_pois()


def resolve_location_name(name):
    """Find a location's content path by display name (e.g. "Palo Alto" → "northamerica/…/paloalto")."""
    content_dir = _content_dir()
    slug = name.lower().replace(" ", "").replace("-", "").replace("_", "")
    for candidate_dir in sorted(content_dir.rglob(slug)):
        if not candidate_dir.is_dir():
            continue
        rel = str(candidate_dir.relative_to(content_dir))
        page = load_page(rel)
        if page and page.page_type == "location":
            return rel
    for candidate_md in sorted(content_dir.rglob(f"{slug}.md")):
        rel = str(candidate_md.relative_to(content_dir).with_suffix(""))
        page = load_page(rel)
        if page and page.page_type == "location":
            return rel
    return None


def _find_city_path(path):
    parts = path.split("/")
    for i in range(len(parts) - 1, 0, -1):
        candidate = "/".join(parts[:i])
        page = load_page(candidate)
        if page and page.page_type == "location":
            return candidate
    return None


def build_city_tag_index(city_path):
    content_dir = _content_dir()
    city_dir = content_dir / city_path
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
        rel = md_file.relative_to(content_dir)
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
    if _city_tag_index is None:
        _city_tag_index = build_city_tag_index(city_path)
    return list(_city_tag_index.get(tag, []))


def _load_page_from_file(file_path, url_path):
    result = _load_md(file_path)
    if not result:
        return None
    meta, body = result
    slug = file_path.stem
    title = meta.get("title", slug)
    raw_type = meta.get("type", "location")
    if raw_type == "poi":
        raw_tags = meta.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [t.strip() for t in raw_tags.split(",")]
        if "city_walks" in raw_tags:
            page_type = "walk"
        elif "vibes" in raw_tags:
            page_type = "vibe"
        elif "neighbourhoods" in raw_tags:
            page_type = "neighbourhood"
        else:
            page_type = "poi"
    else:
        page_type = raw_type
    return Page(
        slug=slug, path=url_path, title=title,
        page_type=page_type, body=body, meta=meta,
    )


def load_page(path):
    """Load a page by its URL path."""
    content_dir = _content_dir()
    slug = path.rsplit("/", 1)[-1] if "/" in path else path

    for md_file in [
        content_dir / path / f"{slug}.md",
        content_dir / f"{path}.md",
    ]:
        if md_file.is_file():
            return _load_page_from_file(md_file, path)

    if "/" in path:
        parent_path, slug = path.rsplit("/", 1)
        md_file = content_dir / parent_path / f"{slug}.md"
        if md_file.is_file():
            return _load_page_from_file(md_file, path)

    return None


def resolve_tag_route(path):
    parts = path.split("/")
    if len(parts) < 2:
        return None, None
    poi_slug = parts[-1]
    for city_len in range(len(parts) - 2, 0, -1):
        city_path = "/".join(parts[:city_len])
        nav_slug = parts[city_len]
        city_page = load_page(city_path)
        if not city_page or city_page.page_type != "location":
            continue
        nav_page = load_page(city_path + "/" + nav_slug)
        if not nav_page or nav_page.page_type not in NAV_TYPES:
            continue
        tag = nav_page.nav_tag
        for poi in find_tagged_pois(city_path, tag):
            if poi.slug == poi_slug:
                return poi, nav_page
        break
    return None, None


@lru_cache(maxsize=1)
def load_tag_index():
    content_dir = _content_dir()
    index = {}
    for md_file in sorted(content_dir.rglob("*.md")):
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
        rel = md_file.relative_to(content_dir)
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
    content_dir = _content_dir()
    continents = []
    CONTINENT_SLUGS = {
        "africa", "asia", "australiaandpacific",
        "europe", "northamerica", "southamerica",
    }
    for entry in sorted(content_dir.iterdir()):
        if entry.is_dir() and entry.name in CONTINENT_SLUGS:
            loc = load_page(entry.name)
            if loc:
                _, locations, _ = loc.children()
                continents.append((loc, locations))
    return continents
