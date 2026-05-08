#!/usr/bin/env python3
"""Export a plan (overview + all stops) as a single standalone HTML file.

Usage:
    python tools/export_plan_html.py <plan-slug> [output.html]
"""
import os, sys, re, base64, mimetypes
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "world66.settings")

import django
django.setup()

from django.test import RequestFactory, Client
from django.contrib.sessions.backends.db import SessionStore
from plans_app.views import _parse_plan, PLANS_DIR
from django.conf import settings


BASE_DIR = Path(settings.BASE_DIR)
STATIC_ROOT = BASE_DIR / "static"
PLANS_STATIC = BASE_DIR / "plans_app" / "static"


def get_client_with_auth(slug):
    """Return a Django test Client with plan auth for the given slug."""
    c = Client()
    # Force a session with the plan authenticated
    s = c.session
    authenticated = s.get("authenticated_plans", [])
    if slug not in authenticated:
        authenticated.append(slug)
    s["authenticated_plans"] = authenticated
    s.save()
    # Also monkey-patch the auth check so export bypasses it entirely
    from plans_app import views as _v
    _orig = _v._plan_authenticated
    _v._plan_authenticated = lambda req, sl: True
    return c


def fetch_page(client, url):
    """Render a page via Django test client, return HTML string."""
    response = client.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"Got {response.status_code} for {url}")
    return response.content.decode("utf-8")


def resolve_static_path(url_path):
    """Map a /static/... URL to a local file path."""
    rel = url_path.lstrip("/")
    # Try plans_app/static first, then global static
    for base in [PLANS_STATIC, STATIC_ROOT]:
        candidate = base / Path(*rel.split("/")[1:])  # strip 'static/' prefix
        if candidate.is_file():
            return candidate
    # Try direct match
    candidate = BASE_DIR / rel
    if candidate.is_file():
        return candidate
    return None


def resolve_plans_image(url_path):
    """Map /plans/image/... to a local file."""
    # /plans/image/<relative-path>
    m = re.match(r"^/plans/image/(.+)$", url_path)
    if m:
        candidate = PLANS_DIR / m.group(1)
        if candidate.is_file():
            return candidate
    return None


def inline_resource(url_path):
    """Return a data URI for a static asset, or None if not found."""
    path = resolve_static_path(url_path) or resolve_plans_image(url_path)
    if not path:
        return None
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def inline_css_urls(css_text, css_url_path):
    """Replace url(...) references inside CSS with data URIs."""
    def replace_url(m):
        raw = m.group(1).strip("'\"")
        if raw.startswith("data:") or raw.startswith("http"):
            return m.group(0)
        # Resolve relative to the CSS file's directory
        css_dir = "/".join(css_url_path.rstrip("/").split("/")[:-1])
        resolved = css_dir + "/" + raw
        data = inline_resource(resolved)
        if data:
            return f"url('{data}')"
        return m.group(0)
    return re.sub(r"url\(([^)]+)\)", replace_url, css_text)


def extract_body(html):
    """Extract the content between <body> and </body>, accounting for <body>
    references inside CSS/script that would fool a naive regex."""
    # Find </head> to skip past all head content (which may contain "<body>" in CSS comments)
    head_end = html.lower().find("</head>")
    search_from = head_end if head_end >= 0 else 0
    body_open = re.search(r"<body[^>]*>", html[search_from:], re.IGNORECASE)
    if not body_open:
        return html
    body_start = search_from + body_open.end()
    body_close = html.lower().rfind("</body>")
    if body_close < 0:
        return html[body_start:]
    return html[body_start:body_close]


def process_html(html, base_url="/"):
    """Inline all CSS, JS, and images into the HTML."""

    # ── Inline <link rel="stylesheet"> ──────────────────────────────────────
    def inline_link(m):
        href = m.group(1)
        if not href.startswith("/static/"):
            return m.group(0)
        path = resolve_static_path(href)
        if not path:
            return m.group(0)
        css_text = path.read_text(errors="ignore")
        css_text = inline_css_urls(css_text, href)
        return f"<style>\n{css_text}\n</style>"

    html = re.sub(
        r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\'][^>]*>',
        inline_link, html
    )
    # Also handle href-before-rel order
    html = re.sub(
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']stylesheet["\'][^>]*>',
        inline_link, html
    )

    # ── Inline <script src="..."> ────────────────────────────────────────────
    def inline_script(m):
        src = m.group(1)
        if src.startswith("http"):
            return m.group(0)  # keep external CDN scripts
        if not src.startswith("/static/"):
            return m.group(0)
        path = resolve_static_path(src)
        if not path:
            return m.group(0)
        js_text = path.read_text(errors="ignore")
        return f"<script>\n{js_text}\n</script>"

    html = re.sub(r'<script[^>]+src=["\']([^"\']+)["\'][^>]*></script>', inline_script, html)

    # ── Inline <img src="..."> ───────────────────────────────────────────────
    def inline_img(m):
        src = m.group(1)
        if src.startswith("data:") or src.startswith("http"):
            return m.group(0)
        data = inline_resource(src)
        if data:
            return m.group(0).replace(src, data)
        return m.group(0)

    html = re.sub(r'<img[^>]+src=["\']([^"\']+)["\']', inline_img, html)

    # ── Inline background-image: url(...) in style attributes ───────────────
    def inline_bg(m):
        url = m.group(1).strip("'\"")
        if url.startswith("data:") or url.startswith("http"):
            return m.group(0)
        data = inline_resource(url)
        if data:
            return m.group(0).replace(url, data)
        return m.group(0)

    html = re.sub(r"background-image:\s*url\('?\"?([^'\")\s]+)'?\"?\)", inline_bg, html)

    # ── Fix nav links to use anchor jumps within the file ───────────────────
    # (leave as-is — they'll just not work offline, which is acceptable)

    return html


def build_standalone(slug, output_path):
    plan = _parse_plan(PLANS_DIR / f"{slug}.md")
    if not plan:
        print(f"Plan not found: {slug}")
        sys.exit(1)

    client = get_client_with_auth(slug)
    stops = plan["stops"]

    sections = []

    # ── Overview page ────────────────────────────────────────────────────────
    print(f"Fetching overview /plans/{slug}/")
    html = fetch_page(client, f"/plans/{slug}/")
    # Extract body content
    body_m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    head_m = re.search(r"<head[^>]*>(.*?)</head>", html, re.DOTALL | re.IGNORECASE)
    head_html = head_m.group(1) if head_m else ""
    body_html = body_m.group(1) if body_m else html

    # Process full page once to extract head (CSS/JS)
    full_inlined = process_html(html)
    # Pull out inlined <style> and <script> blocks from head
    styles = re.findall(r"<style[^>]*>.*?</style>", full_inlined, re.DOTALL)
    scripts_head = re.findall(r"<script[^>]*>.*?</script>", full_inlined[:full_inlined.find("<body")], re.DOTALL)

    shared_head = "\n".join(styles) + "\n" + "\n".join(scripts_head)

    sections.append(("overview", plan["title"], full_inlined))

    # ── Each stop page ───────────────────────────────────────────────────────
    for stop in stops:
        city_slug = stop["city_slug"]
        city = stop["city"]
        url = f"/plans/{slug}/{city_slug}/"
        print(f"Fetching stop {url}")
        try:
            html = fetch_page(client, url)
            inlined = process_html(html)
            sections.append((city_slug, city, inlined))
        except Exception as e:
            print(f"  ⚠ Skipped {url}: {e}")

    # ── Combine into one file with anchor navigation ─────────────────────────
    toc_items = []
    page_divs = []

    for i, (section_id, title, inlined) in enumerate(sections):
        anchor = f"section-{i}"
        toc_items.append(f'<li><a href="#{anchor}">{title}</a></li>')

        # Extract body from inlined page, wrap in a div
        body_content = extract_body(inlined)

        # Strip any <style> blocks that ended up in the body (e.g. from template rendering quirks)
        body_content = re.sub(r"<style[^>]*>.*?</style>", "", body_content, flags=re.DOTALL)

        # Remove nav/footer for non-first sections to reduce repetition
        if i > 0:
            body_content = re.sub(r"<nav[^>]*class=[\"'][^\"']*tabbi-nav[^\"']*[\"'][^>]*>.*?</nav>", "", body_content, flags=re.DOTALL)
            body_content = re.sub(r"<footer[^>]*>.*?</footer>", "", body_content, flags=re.DOTALL)

        # Make map IDs unique so Leaflet doesn't clash across sections
        map_id = f"map-section-{i}"
        body_content = body_content.replace('id="plan-stop-map"', f'id="{map_id}"')
        body_content = body_content.replace('id="plan-overview-map"', f'id="{map_id}"')
        body_content = body_content.replace("'plan-stop-map'", f"'{map_id}'")
        body_content = body_content.replace("'plan-overview-map'", f"'{map_id}'")

        # Register map instance in global registry so IntersectionObserver can
        # call invalidateSize() when the section scrolls into view.
        body_content = re.sub(
            r"(const map = L\.map\('" + re.escape(map_id) + r"')",
            r"window._exportMaps = window._exportMaps || {}; \1",
            body_content,
        )
        body_content = re.sub(
            r"(const map = L\.map\('" + re.escape(map_id) + r"'[^;]+;)",
            r"\1 window._exportMaps['" + map_id + r"'] = map;",
            body_content,
        )

        # Remove duplicate Leaflet CDN script tags (keep only first)
        if i > 0:
            body_content = re.sub(
                r'<script[^>]+unpkg\.com/leaflet[^>]*></script>', '', body_content
            )

        page_divs.append(
            f'<div id="{anchor}" class="export-section">'
            f'<div class="export-section-divider">{"— " + title + " —" if i > 0 else ""}</div>'
            f'{body_content}'
            f'</div>'
        )

    # Collect all <style> blocks from the first page (anywhere — head or body)
    # and deduplicate by content so we don't repeat large CSS blobs.
    first_inlined = sections[0][2]
    seen_styles = []
    seen_hashes = set()
    for m in re.finditer(r"<style[^>]*>(.*?)</style>", first_inlined, re.DOTALL):
        h = hash(m.group(1).strip())
        if h not in seen_hashes:
            seen_hashes.add(h)
            seen_styles.append(m.group(0))
    styles = "\n".join(seen_styles)

    toc_html = f"""
    <div class="export-toc">
      <strong>Contents</strong>
      <ul>{''.join(toc_items)}</ul>
    </div>
    """

    output = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{plan['title']} — Tab.bi</title>
{styles}
<style>
.export-toc {{ background:#FFFBF0; border:1.5px dashed #e0c87a; border-radius:12px; padding:16px 24px; margin:24px auto; max-width:900px; font-family:'Lexend Exa',sans-serif; }}
.export-toc ul {{ margin:8px 0 0; padding-left:20px; }}
.export-toc li {{ margin:4px 0; }}
.export-toc a {{ color:#c89a0a; text-decoration:none; font-weight:600; }}
.export-toc a:hover {{ text-decoration:underline; }}
.export-section {{ border-top: 2px dashed #e0c87a; padding-top:8px; margin-top:40px; }}
.export-section:first-child {{ border-top:none; margin-top:0; }}
.export-section-divider {{ text-align:center; color:#b8960a; font-size:0.78rem; letter-spacing:0.1em; text-transform:uppercase; font-family:'Lexend Exa',sans-serif; margin-bottom:8px; }}
#plan-stop-map, #plan-overview-map {{ height:300px !important; }}
[id^="map-section-"] {{ height:300px !important; }}
</style>
</head>
<body>
{toc_html}
{''.join(page_divs)}
<script>
// Invalidate each Leaflet map when it first scrolls into view,
// so tiles load correctly in the combined single-page export.
(function() {{
  var maps = window._exportMaps || {{}};
  if (!window.IntersectionObserver) {{
    // Fallback: just invalidate all immediately
    Object.values(maps).forEach(function(m) {{ m.invalidateSize(); }});
    return;
  }}
  var observer = new IntersectionObserver(function(entries) {{
    entries.forEach(function(entry) {{
      if (entry.isIntersecting) {{
        var m = maps[entry.target.id];
        if (m) {{ setTimeout(function() {{ m.invalidateSize(); }}, 50); }}
        observer.unobserve(entry.target);
      }}
    }});
  }}, {{ threshold: 0.01 }});
  Object.keys(maps).forEach(function(id) {{
    var el = document.getElementById(id);
    if (el) observer.observe(el);
  }});
}})();
</script>
</body>
</html>"""

    Path(output_path).write_text(output, encoding="utf-8")
    size_kb = Path(output_path).stat().st_size // 1024
    print(f"\n✓ Written to {output_path} ({size_kb} KB)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/export_plan_html.py <plan-slug> [output.html]")
        sys.exit(1)
    slug = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/{slug}.html"
    build_standalone(slug, out)
