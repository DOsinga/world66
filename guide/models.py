"""
Re-exports world66_content.models for the guide app.

Guide-specific additions (load_page_from_branch) live here too.
"""

import subprocess

import frontmatter
from django.conf import settings

from world66_content.models import (  # noqa: F401  (re-exported)
    CONTENT_DIR,
    DISPLAY_PROPERTIES,
    NAV_TYPES,
    Page,
    _find_city_path,
    _load_page_from_file,
    build_city_tag_index,
    find_tagged_pois,
    load_continents,
    load_page,
    load_tag_index,
    resolve_location_name,
    resolve_tag_route,
)


def load_page_from_branch(path, branch):
    """Load a page from a git branch using git show, without touching the filesystem."""
    slug = path.rsplit('/', 1)[-1] if '/' in path else path
    for git_path in [f'content/{path}/{slug}.md', f'content/{path}.md']:
        result = subprocess.run(
            ['git', 'show', f'{branch}:{git_path}'],
            capture_output=True, text=True, check=False,
            cwd=str(settings.BASE_DIR),
        )
        if result.returncode == 0:
            post = frontmatter.loads(result.stdout)
            title = post.metadata.get('title', slug)
            page_type = post.metadata.get('type', 'location')
            return Page(slug=slug, path=path, title=title, page_type=page_type, body=post.content, meta=post.metadata)
    return None
