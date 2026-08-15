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

import bisect
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import frontmatter
from django.conf import settings

from . import github

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


def _score_desc_title_key(page):
    """Sort pages by score descending, then title for stable ties."""
    try:
        score = float(page.meta.get("score", 0) or 0)
    except (TypeError, ValueError):
        score = 0
    return (-score, page.title.casefold())


def _load_md(path):
    """Load and parse a markdown file. Returns (meta, body) or None.

    Raises on invalid frontmatter — content is expected to be valid.
    Run `python3 tools/linter.py` to find and fix broken files.
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
    revision: str = ""      # short hash used in URLs
    source_ref: str = ""    # full git object used for content reads

    def get_absolute_url(self):
        if self.revision:
            return f"/{self.revision}/{self.path}"
        return f"/{self.path}"

    @property
    def url_prefix(self):
        return f"/{self.revision}" if self.revision else ""

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

    # Tags that serve as filterable categories on section pages.
    _CATEGORY_TAGS = {"sight", "museum", "architecture", "neighbourhood", "restaurant", "bar", "market"}

    @property
    def category(self):
        """Derive display category from tags, falling back to legacy field."""
        explicit = self.meta.get("category", "")
        if explicit:
            return explicit
        for t in self.tags:
            if t in self._CATEGORY_TAGS:
                return t.replace("_", " ").title()
        return ""

    @property
    def nav_tag(self):
        """The tag this nav page uses to collect its POIs. Defaults to slug."""
        return self.meta.get("tag", self.slug)

    def breadcrumbs(self):
        crumbs = []
        parts = self.path.split("/")
        for i in range(len(parts)):
            ancestor_path = "/".join(parts[: i + 1])
            if self.source_ref:
                ancestor = load_page_from_revision(
                    ancestor_path, self.source_ref, url_revision=self.revision
                )
            else:
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
        if self.source_ref:
            return self.children_from_revision()

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

        return nav_pages, locations, sorted(pois, key=_score_desc_title_key)

    def children_from_revision(self):
        """Sub-pages in this page's GitHub revision directory, grouped by type."""
        names = _revision_dir_names(self.source_ref, self.path)
        if not names:
            return [], [], []

        dir_names = {n for n in names if not n.endswith(".md")}
        nav_pages = []
        locations = []
        pois = []

        for name in sorted(names):
            if name.endswith(".md"):
                stem = name[:-3]
                if stem == self.slug or stem in dir_names:
                    continue
                page = load_page_from_revision(
                    f"{self.path}/{stem}", self.source_ref, url_revision=self.revision
                )
            elif "." not in name:
                page = load_page_from_revision(
                    f"{self.path}/{name}", self.source_ref, url_revision=self.revision
                )
            else:
                continue

            if not page:
                continue
            if page.page_type in NAV_TYPES:
                nav_pages.append(page)
            elif page.page_type == "poi":
                pois.append(page)
            else:
                locations.append(page)

        return nav_pages, locations, sorted(pois, key=_score_desc_title_key)

    def children_from_branch(self, branch: str):
        """Compatibility wrapper for callers that still pass a branch name."""
        names = _revision_dir_names(branch, self.path)
        dir_names = {n for n in names if not n.endswith(".md")}

        nav_pages, locations, pois = [], [], []

        for name in sorted(names):
            if name.endswith(".md"):
                stem = name[:-3]
                if stem == self.slug or stem in dir_names:
                    continue
                page = load_page_from_branch(f"{self.path}/{stem}", branch)
            elif "." not in name:
                page = load_page_from_branch(f"{self.path}/{name}", branch)
            else:
                continue

            if not page:
                continue
            if page.page_type in NAV_TYPES:
                nav_pages.append(page)
            elif page.page_type == "poi":
                pois.append(page)
            else:
                locations.append(page)

        return nav_pages, locations, pois

    def tagged_pois(self, _city_tag_index=None):
        """Return POIs tagged with this nav page's tag, found anywhere in the city.

        Also includes POIs in the legacy section subdirectory (files that
        predate the tag system and haven't been migrated yet).

        Pass _city_tag_index (from build_city_tag_index) to avoid repeated scans.
        """
        city_path = _find_city_path(self.path, self.source_ref, self.revision)
        if not city_path:
            return []
        # Only aggregate tagged POIs when the parent is a city, not a country/region.
        # Country- and region-level sections are editorial text, not POI aggregators.
        city_page = load_page(city_path) if not self.source_ref else load_page_from_revision(city_path, self.source_ref, self.revision)
        if city_page and city_page.meta.get('loc_type') not in ('city', 'feature', None):
            return self._legacy_dir_pois()
        tag = self.nav_tag
        by_tag = find_tagged_pois(
            city_path, tag, _city_tag_index=_city_tag_index,
            revision=self.source_ref, url_revision=self.revision,
        )

        # Legacy: also scan the section's own subdirectory for untagged POIs
        legacy = self._legacy_dir_pois()
        seen = {p.path for p in by_tag}
        for p in legacy:
            if p.path not in seen:
                by_tag.append(p)

        return sorted(by_tag, key=_score_desc_title_key)

    def _legacy_dir_pois(self):
        """POIs inside this page's own subdirectory (pre-tag content)."""
        if self.source_ref:
            pois = _revision_dir_pois(
                self.source_ref, self.path, self.path, self.revision
            )
            if not pois and "/" in self.path:
                fallback_dir = f'{self.path.rsplit("/", 1)[0]}/{self.slug}'
                pois = _revision_dir_pois(
                    self.source_ref, fallback_dir, self.path, self.revision
                )
            return sorted(pois, key=_score_desc_title_key)

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
        return sorted(pois, key=_score_desc_title_key)

    # Keep old name for call sites not yet updated
    def pois(self):
        return self.tagged_pois()


def _find_city_path(path, revision=None, url_revision=None):
    """Return the path of the nearest ancestor page with type 'location'."""
    parts = path.split("/")
    for i in range(len(parts) - 1, 0, -1):
        candidate = "/".join(parts[:i])
        page = (
            load_page_from_revision(candidate, revision, url_revision=url_revision)
            if revision else load_page(candidate)
        )
        if page and page.page_type == "location":
            return candidate
    return None


def build_city_tag_index(city_path, revision=None, url_revision=None):
    """Scan all POI files under city_path once and return {tag: [Page, ...]}."""
    if revision:
        return _build_city_tag_index_from_revision(city_path, revision, url_revision)

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
        if meta.get("type") not in ("poi", "neighbourhood", "theme"):
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


def find_tagged_pois(city_path, tag, _city_tag_index=None, revision=None, url_revision=None):
    """Return POIs under city_path tagged with tag.

    Pass _city_tag_index (from build_city_tag_index) to avoid repeated scans.
    """
    if _city_tag_index is None:
        _city_tag_index = build_city_tag_index(city_path, revision, url_revision)
    return sorted(_city_tag_index.get(tag, []), key=_score_desc_title_key)


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


def _load_page_from_git_path(git_path, url_path, revision, url_revision=None):
    """Load a Page from a content/*.md path in a GitHub revision."""
    text = github.get_file_text(revision, git_path)
    if text is None:
        return None
    post = frontmatter.loads(text)
    slug = Path(git_path).stem
    title = post.metadata.get("title", slug)
    page_type = post.metadata.get("type", "location")
    return Page(
        slug=slug, path=url_path, title=title, page_type=page_type,
        body=post.content, meta=post.metadata,
        revision=url_revision or revision[:10], source_ref=revision,
    )


def load_page_from_revision(path, revision, url_revision=None):
    """Load a page from a GitHub revision without touching the filesystem."""
    slug = path.rsplit("/", 1)[-1] if "/" in path else path
    for git_path in [f"content/{path}/{slug}.md", f"content/{path}.md"]:
        page = _load_page_from_git_path(git_path, path, revision, url_revision)
        if page:
            return page
    return None


def load_page_from_branch(path, branch):
    """Compatibility wrapper for old ?branch= callers."""
    return load_page_from_revision(path, branch, url_revision=branch)


def _revision_dir_names(revision, url_path):
    """Return immediate child names for a content directory at a GitHub revision."""
    names = [item["name"] for item in github.list_dir(revision, f"content/{url_path}")]
    return sorted(set(names))


def _revision_dir_pois(revision, dir_url_path, page_url_base, url_revision=None):
    pois = []
    for name in _revision_dir_names(revision, dir_url_path):
        if not name.endswith(".md"):
            continue
        page = _load_page_from_git_path(
            f"content/{dir_url_path}/{name}",
            f"{page_url_base}/{name[:-3]}",
            revision,
            url_revision,
        )
        if page and page.page_type == "poi":
            pois.append(page)
    return pois


def _build_city_tag_index_from_revision(city_path, revision, url_revision=None):
    index = {}
    seen = set()
    for git_path in sorted(github.iter_files(revision, f"content/{city_path}")):
        if not git_path.endswith(".md"):
            continue
        text = github.get_file_text(revision, git_path)
        if text is None:
            continue
        post = frontmatter.loads(text)
        if post.metadata.get("type") not in ("poi", "neighbourhood", "theme"):
            continue
        raw_tags = post.metadata.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [t.strip() for t in raw_tags.split(",")]
        if not raw_tags:
            continue
        rel = Path(git_path).relative_to("content")
        parts = list(rel.parts)
        stem = parts[-1][:-3]
        url_path = "/".join(parts[:-1] + [stem])
        if url_path in seen:
            continue
        seen.add(url_path)
        page = _load_page_from_git_path(git_path, url_path, revision, url_revision)
        if page:
            for tag in raw_tags:
                index.setdefault(tag, []).append(page)
    return index


def load_page(path):
    """Load a page by its URL path."""
    slug = path.rsplit("/", 1)[-1] if "/" in path else path

    for md_file in [
        CONTENT_DIR / f"{path}.md",
        CONTENT_DIR / path / f"{slug}.md",
    ]:
        if md_file.is_file():
            return _load_page_from_file(md_file, path)

    if "/" in path:
        parent_path, slug = path.rsplit("/", 1)
        md_file = CONTENT_DIR / parent_path / f"{slug}.md"
        if md_file.is_file():
            return _load_page_from_file(md_file, path)

    return None


def resolve_tag_route(path, revision=None, url_revision=None):
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

        city_page = (
            load_page_from_revision(city_path, revision, url_revision=url_revision)
            if revision else load_page(city_path)
        )
        if not city_page or city_page.page_type != "location":
            continue

        nav_page = (
            load_page_from_revision(
                city_path + "/" + nav_slug, revision, url_revision=url_revision
            )
            if revision else load_page(city_path + "/" + nav_slug)
        )
        if not nav_page or nav_page.page_type not in NAV_TYPES:
            continue

        # Find a POI in this city tagged with the nav page's tag
        tag = nav_page.nav_tag
        for poi in find_tagged_pois(
            city_path, tag, revision=revision, url_revision=url_revision
        ):
            if poi.slug == poi_slug:
                return poi, nav_page

        break  # found valid city/nav, but no matching poi

    return None, None


def find_locations_tagged(slug, feature_path):
    """Return location pages that carry `slug` in their tags.

    Scans only the parent directory of the feature page (and its immediate
    children), which is where cities that tag into a feature always live.
    Falls back to the grandparent if the parent scan finds nothing.
    """
    results = []
    if "/" not in feature_path:
        return results

    parent_path = feature_path.rsplit("/", 1)[0]
    search_dirs = [CONTENT_DIR / parent_path]
    # Also try grandparent (for features nested one level deeper than their cities)
    if "/" in parent_path:
        search_dirs.append(CONTENT_DIR / parent_path.rsplit("/", 1)[0])

    seen = set()
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for md_file in sorted(search_dir.rglob("*.md")):
            result = _load_md(md_file)
            if not result:
                continue
            meta, _ = result
            if meta.get("type") != "location":
                continue
            raw_tags = meta.get("tags", [])
            if isinstance(raw_tags, str):
                raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            if slug not in raw_tags:
                continue
            rel = md_file.relative_to(CONTENT_DIR)
            parts = list(rel.parts)
            stem = parts[-1][:-3]
            if len(parts) >= 2 and stem == parts[-2]:
                url_path = "/".join(parts[:-1])
            else:
                url_path = "/".join(parts[:-1] + [stem]) if len(parts) > 1 else stem
            if url_path in seen:
                continue
            seen.add(url_path)
            page = _load_page_from_file(md_file, url_path)
            if page:
                results.append(page)
        if results:
            break  # found in parent dir, no need to scan grandparent

    return results


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
def load_story_pois():
    """Return all POIs tagged 'story' with their parent location title. Cached for the process lifetime; caller randomises."""
    result = []
    for md_file in sorted(CONTENT_DIR.rglob("*.md")):
        r = _load_md(md_file)
        if not r:
            continue
        meta, body = r
        if meta.get("type") != "poi":
            continue
        raw_tags = meta.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        tag_set = set(raw_tags)
        if "story" not in tag_set or tag_set & {"books", "getting_there", "hotel", "accommodation"}:
            continue
        rel = md_file.relative_to(CONTENT_DIR)
        parts = list(rel.parts)
        stem = parts[-1][:-3]
        if len(parts) >= 2 and stem == parts[-2]:
            url_path = "/".join(parts[:-1])
        else:
            url_path = "/".join(parts[:-1] + [stem]) if len(parts) > 1 else stem
        page = _load_page_from_file(md_file, url_path)
        if not page:
            continue
        parent_path = "/".join(url_path.split("/")[:-1])
        parent = load_page(parent_path) if parent_path else None
        result.append({
            "page": page,
            "story": meta.get("story", "") or body[:400],
            "snippet": meta.get("snippet", ""),
            "location": parent.title if parent else "",
        })
    return result


_CITY_SCORE_THRESHOLDS = {
    "africa": 0.52,
    "caribbean": 0.44,
    "centralamerica": 0.46,
    "southamerica": 0.48,
    "middleeast": 0.46,
    "australiaandpacific": 0.50,
    "asia": 0.60,
    "northamerica": 0.60,
    "europe": 0.65,
}
_COUNTRY_FEATURED_FALLBACK_THRESHOLD = 0.50
_COUNTRY_POI_FEATURED_FALLBACK_THRESHOLD = 9.0


@lru_cache(maxsize=1)
def count_content_pages():
    """Return the number of markdown pages in the content tree."""
    return sum(1 for _ in CONTENT_DIR.rglob("*.md"))


@lru_cache(maxsize=1)
def load_featured_cities():
    """Return featured location pages at city level, with at least one strong entry per country."""
    result = []
    country_best = {}
    country_best_poi = {}
    represented_countries = set()

    def _city_candidate(city_file, cont_name, country_name, state_name=None):
        r = _load_md(city_file)
        if not r:
            return None
        meta, body = r
        if meta.get("type") != "location":
            return None
        score = float(meta.get("score", 0) or 0)
        image = meta.get("image", "")
        if not image:
            return None
        # At depth-3 (no state_name), skip entries that are state/province containers —
        # i.e. pages whose corresponding directory holds child location pages (cities).
        # Those cities are already captured at depth-4.
        if not state_name:
            sub = city_file.parent / city_file.stem
            if sub.is_dir():
                for child in sorted(sub.iterdir()):
                    if child.is_file() and child.suffix == ".md":
                        child_r = _load_md(child)
                        if child_r and child_r[0].get("type") == "location":
                            return None  # this is a state/region page, not a city
                        break
        stem = city_file.stem
        if state_name:
            if stem == state_name:
                url_path = f"{cont_name}/{country_name}/{state_name}"
            else:
                url_path = f"{cont_name}/{country_name}/{state_name}/{stem}"
            image_candidates = [
                f"{url_path}/{image}",
                f"{cont_name}/{country_name}/{state_name}/{image}",
                f"{cont_name}/{country_name}/{image}",
            ]
        else:
            if stem == country_name:
                url_path = f"{cont_name}/{country_name}"
            else:
                url_path = f"{cont_name}/{country_name}/{stem}"
            image_candidates = [
                f"{url_path}/{image}",
                f"{cont_name}/{country_name}/{image}",
            ]
        for candidate in image_candidates:
            if (CONTENT_DIR / candidate).is_file():
                image_url = f"/content-image/{candidate}"
                break
        else:
            return None
        page = _load_page_from_file(city_file, url_path)
        if not page:
            return None
        country = load_page(f"{cont_name}/{country_name}")
        return {
            "page": page,
            "image_url": image_url,
            "country": country.title if country else "",
            "lat": meta.get("latitude"),
            "lng": meta.get("longitude"),
            "score": score,
        }

    def _top_poi_score(city_file):
        top_score = 0
        sub = city_file.parent / city_file.stem
        if not sub.is_dir():
            return top_score
        for child in sorted(sub.iterdir()):
            if not child.is_file() or child.suffix != ".md":
                continue
            child_r = _load_md(child)
            if not child_r or child_r[0].get("type") != "poi":
                continue
            try:
                score = float(child_r[0].get("score", 0) or 0)
            except (TypeError, ValueError):
                score = 0
            top_score = max(top_score, score)
        return top_score

    def _try_city(city_file, cont_name, country_name, state_name=None):
        candidate = _city_candidate(city_file, cont_name, country_name, state_name)
        if not candidate:
            return
        country_key = (cont_name, country_name)
        score = candidate["score"]
        top_poi_score = _top_poi_score(city_file)
        if top_poi_score >= _COUNTRY_POI_FEATURED_FALLBACK_THRESHOLD:
            current = country_best_poi.get(country_key)
            if (
                not current
                or top_poi_score > current["top_poi_score"]
                or (
                    top_poi_score == current["top_poi_score"]
                    and score > current["score"]
                )
            ):
                candidate["top_poi_score"] = top_poi_score
                country_best_poi[country_key] = candidate
        if score >= _COUNTRY_FEATURED_FALLBACK_THRESHOLD:
            current = country_best.get(country_key)
            if not current or score > current["score"]:
                country_best[country_key] = candidate
        threshold = _CITY_SCORE_THRESHOLDS.get(cont_name, 0.60)
        if score >= threshold:
            represented_countries.add(country_key)
            result.append(candidate)

    for cont_dir in sorted(CONTENT_DIR.iterdir()):
        if not cont_dir.is_dir():
            continue
        for country_dir in sorted(cont_dir.iterdir()):
            if not country_dir.is_dir():
                continue
            for entry in sorted(country_dir.iterdir()):
                if entry.is_file() and entry.suffix == ".md":
                    # depth-3: continent/country/city.md
                    _try_city(entry, cont_dir.name, country_dir.name)
                elif entry.is_dir():
                    # depth-4: continent/country/state/city.md
                    for city_file in sorted(entry.iterdir()):
                        if city_file.is_file() and city_file.suffix == ".md":
                            _try_city(city_file, cont_dir.name, country_dir.name, entry.name)
    country_fallbacks = {
        **country_best,
        **country_best_poi,
    }
    for country_key, candidate in sorted(
        country_fallbacks.items(),
        key=lambda item: (
            -item[1].get("top_poi_score", 0),
            -item[1]["score"],
            item[0],
        ),
    ):
        if country_key not in represented_countries:
            result.append(candidate)
    return result


@lru_cache(maxsize=1)
def load_continents():
    """Load top-level locations with their children (countries)."""
    continents = []
    CONTINENT_SLUGS = {
        "africa", "asia", "australiaandpacific",
        "europe", "northamerica", "southamerica",
    }
    for entry in sorted(CONTENT_DIR.iterdir()):
        if entry.is_dir() and entry.name in CONTINENT_SLUGS:
            loc = load_page(entry.name)
            if loc:
                _, locations, _ = loc.children()
                continents.append((loc, locations))
    return continents


DIMENSION_FIELDS = ("heritage", "vibrancy", "nature", "off_the_beaten_track")
DIMENSION_LABELS = {
    "heritage": "Heritage",
    "vibrancy": "Vibrancy",
    "nature": "Nature",
    "off_the_beaten_track": "Off The Beaten Track",
}
# Theoretical max Euclidean distance between two points in the N-dim 0-10
# score space (sqrt(N * 10**2)) — used to normalize distance into a 0-100
# "match" percentage for the similar-places chips.
_MAX_DIMENSION_DISTANCE = (len(DIMENSION_FIELDS) * 10 ** 2) ** 0.5


@lru_cache(maxsize=1)
def load_dimension_index():
    """Scan all content files and return {path: (5 dimension scores)} for every
    location that has all five (see tools/backfill_dimension_scores.py)."""
    index = {}
    for md_file in sorted(CONTENT_DIR.rglob("*.md")):
        result = _load_md(md_file)
        if not result:
            continue
        meta, _ = result
        if meta.get("type") != "location":
            continue
        if any(meta.get(field) is None for field in DIMENSION_FIELDS):
            continue
        rel = md_file.relative_to(CONTENT_DIR)
        parts = list(rel.parts)
        stem = parts[-1][:-3]
        if len(parts) >= 2 and stem == parts[-2]:
            url_path = "/".join(parts[:-1])
        else:
            url_path = "/".join(parts[:-1] + [stem]) if len(parts) > 1 else stem
        index[url_path] = tuple(float(meta[field]) for field in DIMENSION_FIELDS)
    return index


@lru_cache(maxsize=1)
def _sorted_dimension_scores():
    """One sorted list of scores per dimension field, for percentile lookups."""
    index = load_dimension_index()
    return {
        field: sorted(vector[i] for vector in index.values())
        for i, field in enumerate(DIMENSION_FIELDS)
    }


def dimension_percentile(field, value):
    """Return what percent of scored locations this value beats or ties on
    `field`, as a "top N%" figure (100 = uniquely lowest, ~0 = highest)."""
    scores = _sorted_dimension_scores()[field]
    rank_from_bottom = bisect.bisect_left(scores, value)
    return 100 * (len(scores) - rank_from_bottom) / len(scores)


def _ranked_by_distance(path):
    """[(other_path, distance), ...] sorted nearest-first, excluding path itself."""
    index = load_dimension_index()
    vector = index.get(path)
    if vector is None:
        return []
    return sorted(
        (
            (other, sum((a - b) ** 2 for a, b in zip(vector, index[other])) ** 0.5)
            for other in index if other != path
        ),
        key=lambda pair: pair[1],
    )


def _country_path(path):
    """First two path segments (continent/country) — country pages never
    nest deeper than that, regions/cities/features are always below."""
    parts = path.split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else path


@lru_cache(maxsize=1)
def _country_dimension_ranks():
    """{path: {field: (rank, total)}} — 1-based rank within the same country
    (see _country_path) for each dimension. Computed once per process from
    the already-loaded dimension index (grouping + sorting ~9k in-memory
    entries), not a filesystem scan, so it's cheap even without warming —
    warmed anyway in guide/apps.py alongside load_dimension_index()."""
    index = load_dimension_index()
    by_country = {}
    for path, vector in index.items():
        by_country.setdefault(_country_path(path), []).append((path, vector))

    ranks = {}
    for entries in by_country.values():
        total = len(entries)
        for i, field in enumerate(DIMENSION_FIELDS):
            ranked = sorted(entries, key=lambda e: e[1][i], reverse=True)
            for rank, (p, _) in enumerate(ranked, start=1):
                ranks.setdefault(p, {})[field] = (rank, total)
    return ranks


def dimension_country_rank(path, field):
    """1-based (rank, total) for path within its own country on field, or
    (None, 0) if path isn't in the scored index at all."""
    return _country_dimension_ranks().get(path, {}).get(field, (None, 0))


def find_similar_with_match_grouped(path, k=3):
    """Like find_similar_by_scores, but split into (same_country, other_country)
    lists of up to k (path, match_pct) pairs each, nearest-first within each
    group. match_pct is the distance normalized against the theoretical max
    distance in this space."""
    country = _country_path(path)
    same, other = [], []
    for other_path, distance in _ranked_by_distance(path):
        if len(same) >= k and len(other) >= k:
            break
        match_pct = round(100 * (1 - distance / _MAX_DIMENSION_DISTANCE))
        bucket = same if _country_path(other_path) == country else other
        if len(bucket) < k:
            bucket.append((other_path, match_pct))
    return same, other


def find_dimension_alternatives(path, k=3):
    """For each dimension, up to k "nearby" locations (sharing this path's
    immediate parent directory — the region/country it actually sits in, not
    just the same country broadly) that beat it on that dimension, highest
    first. Returns {field: [(other_path, other_score), ...]} — an empty list
    when nothing under the same parent scores higher, including when there
    are no other scored siblings at all."""
    index = load_dimension_index()
    vector = index.get(path)
    candidates = {field: [] for field in DIMENSION_FIELDS}
    if vector is None or "/" not in path:
        return candidates

    parent = path.rsplit("/", 1)[0]
    for other_path, other_vector in index.items():
        if other_path == path or other_path.rsplit("/", 1)[0] != parent:
            continue
        for i, field in enumerate(DIMENSION_FIELDS):
            if other_vector[i] > vector[i]:
                candidates[field].append((other_path, other_vector[i]))

    return {
        field: sorted(items, key=lambda pair: pair[1], reverse=True)[:k]
        for field, items in candidates.items()
    }
