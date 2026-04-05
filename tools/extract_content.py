#!/usr/bin/env python3
"""
Step 3: Extract clean content from downloaded World66 pages.

Handles two page templates:
- Oberon era (early): content in <td id=mainbody>
- Internet Brands era (later): content in <div id="column2" class="wide KonaBody">

Extracts the travel guide content into clean Markdown files.
"""

import json
import os
import re
import sys

import frontmatter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
CONTENT_DIR = os.path.join(SCRIPT_DIR, "..", "content")
INDEX_FILE = os.path.join(SCRIPT_DIR, "site_index.json")
REDIRECTS_FILE = os.path.join(SCRIPT_DIR, "..", "redirects.json")

# Sub-regions to flatten: remove the sub-region from the path
# e.g. asia/middleeast/turkey -> asia/turkey
SUBREGIONS_TO_FLATTEN = {
    "asia/centralasia",
    "asia/middleeast",
    "asia/northeastasia",
    "asia/south",
    "asia/southasia",
    "asia/southeastasia",
    "centralamericathecaribbean/thecaribbean",
    "centralamericathecaribbean/theccribbean",
}


def extract_between(html, start_pattern, end_pattern):
    """Extract text between two regex patterns."""
    m = re.search(start_pattern, html, re.IGNORECASE)
    if not m:
        return None
    start_pos = m.end()
    m2 = re.search(end_pattern, html[start_pos:], re.IGNORECASE)
    if not m2:
        return html[start_pos:]
    return html[start_pos : start_pos + m2.start()]


def extract_main_content(html):
    """Extract the main content area from either template."""
    # Try Internet Brands template first (more specific)
    content = extract_between(
        html,
        r'<div[^>]*id="column2"[^>]*class="wide KonaBody"[^>]*>',
        r'<div[^>]*id="column3"',
    )

    if not content:
        # Also try with legacy-content div inside
        content = extract_between(
            html,
            r"<div[^>]*class='legacy-content'[^>]*>",
            r'<div[^>]*class=[\'"]endOfPageAd',
        )

    if not content:
        # Try Oberon template
        content = extract_between(
            html, r"<td[^>]*id=mainbody[^>]*>", r"<td[^>]*id=colright[^>]*>"
        )

    if not content:
        # Last resort: look for any mainbody or content div
        content = extract_between(html, r'<td[^>]*id="?mainbody"?[^>]*>', r"</td>")

    if not content:
        # Oberon v2 template: content in <div id="maincol">
        content = extract_between(
            html,
            r'<div[^>]*id="?maincol"?[^>]*>',
            r'<div[^>]*id="?rightcol"?',
        )

    if not content:
        # Oberon v3 template: content in <div id="centercontent">
        content = extract_between(
            html,
            r'<div[^>]*id="?centercontent"?[^>]*>',
            r'<div[^>]*id="?rightcontent"?',
        )

    if not content:
        # ASP-era template: content in <td class=txt> after <H1>
        content = extract_between(
            html,
            r'<td[^>]*class=txt[^>]*>\s*<H1>',
            r'</td>\s*</tr>\s*</table>\s*</td>\s*</tr>\s*</table>\s*</td>',
        )
        # Re-add the H1 since our start pattern consumed it
        if content:
            m = re.search(r'<H1>(.*?)</H1>', html, re.IGNORECASE | re.DOTALL)
            if m:
                content = f"<h1>{m.group(1)}</h1>{content}"

    return content


def extract_title(html):
    """Extract the page title."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    title = m.group(1).strip()
    # Clean up common title patterns
    for suffix in [
        " - World66",
        " | World66",
        " :: World66",
        " - the travel guide you write",
        "World66, the travel guide you write: ",
        " Travel Guide",
        " travel guide",
        " travelguide",
    ]:
        title = title.replace(suffix, "")
    # Handle "Best Restaurants Algiers | Algiers Eating Out" style IB titles
    if "|" in title:
        title = title.split("|")[-1].strip()
    return title.strip()


def extract_h1(content):
    """Extract the first h1 from content."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL | re.IGNORECASE)
    if m:
        return strip_tags(m.group(1)).strip()
    return ""


def strip_tags(html):
    """Remove HTML tags, decode entities, clean whitespace."""
    # Remove script and style blocks
    text = re.sub(
        r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(
        r"<noscript[^>]*>.*?</noscript>", "", text, flags=re.DOTALL | re.IGNORECASE
    )

    # Remove Oberon v2 cruft (featured image tables, pointofinterest wrappers)
    text = re.sub(r'<table[^>]*><tr><td[^>]*class="?featured"?[^>]*>.*?</table>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<p[^>]*class="?pointofinterest"?[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*class="?body(?:Text)?"?[^>]*>', '\n\n', text, flags=re.IGNORECASE)

    # Remove ASP-era cruft (dropdown selects, author lines, action links)
    text = re.sub(r"<form[^>]*>.*?</form>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<select[^>]*>.*?</select>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<i>Author:.*?</i>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<A[^>]*>Comment it</A>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<A[^>]*>Add a Highlight</A>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<A[^>]*>Reformulate text</A>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<IMG[^>]*Icons/Line\.Gif[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r": General", "", text)  # Strip ": General" from H1 titles

    # Remove image-related divs (upload/change buttons)
    text = re.sub(
        r'<div[^>]*class="?photoBox"?[^>]*>.*?</div>\s*</div>',
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r'<div[^>]*class="?locationImage"?[^>]*>.*?</div>',
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r'<span[^>]*class="?imageSubscript"?[^>]*>.*?</span>',
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r'<img[^>]*class="?locationImage"?[^>]*/?\s*>', "", text, flags=re.IGNORECASE
    )

    # Remove ad divs
    text = re.sub(
        r'<div[^>]*id="?ads_\d+"?[^>]*>.*?</div>',
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r'<div[^>]*id="?horizontalad"?[^>]*>.*?</div>',
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r'<div[^>]*class=[\'"]endOfPageAd[^>]*>.*',
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Remove edit links
    text = re.sub(r"<a[^>]*>\[edit this\]</a>", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r'<a[^>]*class="?edit"?[^>]*>Edit This</a>', "", text, flags=re.IGNORECASE
    )

    # Remove "add" links
    text = re.sub(r"<a[^>]*>\[Add[^\]]*\]</a>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<a[^>]*>\[add[^\]]*\]</a>", "", text, flags=re.IGNORECASE)

    # Remove "Nearby X Guides" sections at the bottom
    text = re.sub(
        r'<div[^>]*class="[^"]*csection-list[^"]*"[^>]*>.*',
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Convert structural HTML to markdown-ish
    text = re.sub(
        r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", text, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", text, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r"<h4[^>]*>(.*?)</h4>", r"\n#### \1\n", text, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.DOTALL | re.IGNORECASE)

    # Convert links - keep internal World66 links as relative paths
    def convert_link(m):
        href = m.group(1)
        link_text = m.group(2)
        # Skip image/upload/change/edit links
        if any(
            x in href.lower()
            for x in [
                "imagechange", "imageupload", "image/change", "image/upload",
                "modify", "addnew", "addchild", "editpage.asp",
                "comment.asp", "link.asp",
            ]
        ):
            return link_text
        # Strip ASP-era links (can't resolve numeric IDs)
        if ".asp" in href.lower():
            return link_text
        # Strip "Rate it" text
        link_text_clean = re.sub(r"Rate it", "", link_text).strip()
        if not link_text_clean:
            return ""
        # Clean world66 URLs to relative
        href = re.sub(r"https?://(?:www\.)?world66\.com", "", href)
        # Flatten sub-region paths in links
        for subregion in SUBREGIONS_TO_FLATTEN:
            href = href.replace("/" + subregion + "/", "/" + subregion.split("/")[0] + "/")
        if href and link_text_clean:
            return f"[{link_text_clean}]({href})"
        return link_text_clean

    text = re.sub(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        convert_link,
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # List items
    text = re.sub(
        r"<li[^>]*>(.*?)</li>", r"- \1", text, flags=re.DOTALL | re.IGNORECASE
    )

    # Paragraphs and breaks
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)

    # Table handling - extract cell content with spaces
    text = re.sub(r"</?table[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?tr[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?td[^>]*>", " ", text, flags=re.IGNORECASE)

    # Remove remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&mdash;", "—")
    text = text.replace("&ndash;", "–")
    text = text.replace("&laquo;", "«")
    text = text.replace("&raquo;", "»")
    text = text.replace("&copy;", "(c)")
    # Numeric entities
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)

    # Clean up leftover "Rate it" text
    text = re.sub(r"Rate it", "", text)

    # --- #12: Strip imported page chrome / old site mechanism fragments ---

    # 12a: Site tagline
    text = re.sub(r"The best resource for sights, hotels, restaurants, bars, what to do and see\s*", "", text)

    # 12b: Page generation timestamp
    text = re.sub(r"Page last generated on \w+ \d+:\d+\s*", "", text)
    text = re.sub(r"-->\s*", "", text)  # Stray HTML comment closers

    # 12c: Wikitravel cross-promotion
    text = re.sub(r"Additional travel guides are available in ten languages at \[?\*?\*?Wikitravel\.org\*?\*?\]?\(?[^)]*\)?\s*", "", text)
    text = re.sub(r"Additional travel guides.*?wikitravel\.org[^\n]*\n?", "", text, flags=re.IGNORECASE)

    # 12d: Attribution boilerplate
    text = re.sub(r"\*?Part or or all of this text stems from the original article at:.*?\n", "", text)
    text = re.sub(r"\*?Part or all of this text stems from the original article at:.*?\n", "", text)

    # 12e: Change history / contributor logs
    text = re.sub(r"\*?\*?Change history\*?\*?\s*\n(?:.*?/member/.*?\n)*", "", text)
    text = re.sub(r"#{1,4}\s*Contributors\s*\n(?:.*?\n)*?(?=\n[^A-Za-z]|\n#|\Z)", "", text)
    text = re.sub(r"(?:Orginal|Original) article by \[.*?\]\(/member/.*?\).*?\n", "", text)
    text = re.sub(r"\b(?:new|change|edit)\s+by\s+\[.*?\]\(/member/.*?\).*?\n", "", text, flags=re.IGNORECASE)
    text = re.sub(r"by \[[^\]]+\]\(/member/[^)]+\)\s*\n?", "", text)
    text = re.sub(r"\[/member/[^\]]+\]", "", text)
    text = re.sub(r"\(/member/[^)]+\)", "", text)

    # 12f: Subsections navigation blocks (rendered dynamically by the site)
    text = re.sub(r"## Subsections\s*\n(?:\[.*?\]\(.*?\)\s*\n?)*", "", text)
    text = re.sub(r"## Sub sections\s*\n(?:\[.*?\]\(.*?\)\s*\n?)*", "", text)

    # 12g: Spam detection - remove pages that are clearly e-commerce spam
    spam_markers = ["moncler", "replica watches", "louis vuitton", "cheap jerseys",
                    "ugg boots", "christian louboutin", "nike air max", "add to cart"]
    if any(marker in text.lower() for marker in spam_markers):
        return ""  # Return empty so the page gets skipped

    # Wikitravel references in body text
    text = re.sub(r"More information on .+ Travel at Wikitravel\.org\s*\n?", "", text)
    text = re.sub(r"[^\n]*Wikitravel[^\n]*\n?", "", text, flags=re.IGNORECASE)

    # Footer partner links
    text = re.sub(r"- \[Wikitravel Press\].*?\n", "", text)
    text = re.sub(r"- \[Adventure Travel\].*?\n", "", text)
    text = re.sub(r"- \[Cheap Airline Tickets\].*?\n", "", text)
    text = re.sub(r"- \[Cruises\].*?\n", "", text)
    text = re.sub(r"- \[Virtual Tours\].*?\n", "", text)
    text = re.sub(r"partner sites:\s*\n?", "", text, flags=re.IGNORECASE)

    # 12h: BBCode fragments
    text = re.sub(r"\[url=([^\]]+)\]([^\[]+)\[/url\]", r"[\2](\1)", text)

    # Dead member links
    text = re.sub(r"\[([^\]]+)\]\(/member/[^)]+\)", r"\1", text)

    # "back to X" navigation links
    text = re.sub(r"\[?back to [^\]]*\]?\(?[^)]*\)?\s*\n?", "", text, flags=re.IGNORECASE)

    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)  # Collapse horizontal whitespace
    text = re.sub(r"\n[ \t]+", "\n", text)  # Remove leading whitespace on lines
    text = re.sub(r"[ \t]+\n", "\n", text)  # Remove trailing whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse multiple blank lines

    return text.strip()


def extract_properties(content):
    """Extract structured properties from a propertyBlock table."""
    props = {}
    block = extract_between(content, r'<div[^>]*class="?propertyBlock"?[^>]*>', r'</table>')
    if not block:
        return props

    # Normalize property names
    PROP_NAMES = {
        "address": "address", "addresss": "address", "addres": "address",
        "addess": "address", "adress": "address", ".address": "address",
        "tel": "phone", "tel.": "phone", "tek": "phone", "tell": "phone",
        "url": "url",
        "email": "email", "e-mail": "email",
        "openinghours": "opening_hours", "openings": "opening_hours",
        "hours": "opening_hours", "open": "opening_hours",
        "closingtime": "closing_time",
        "priceofmenu": "price", "price": "price",
        "admission": "admission", "entrancefee": "admission",
        "accessibility": "accessibility",
        "isbn": "isbn", "author": "author", "subject": "subject",
        "date": "date",
        "connection": "connections", "connections": "connections",
        "gettingthere": "getting_there",
        "zipcode": "zipcode",
        "costofdoubleforanight": "price_per_night",
    }

    for m in re.finditer(
        r'<tr><td[^>]*>([^<]+?)(?::?\s*)(?:</td>)?\s*<td[^>]*>(.*?)</tr>',
        block, re.DOTALL | re.IGNORECASE
    ):
        name = m.group(1).strip().rstrip(':').lower()
        val = re.sub(r'<[^>]+>', '', m.group(2)).strip()

        if name == 'world66 rating' or not val or val == 'None':
            continue

        # Normalize name
        canon = PROP_NAMES.get(name, name)
        # Clean up email obfuscation
        if canon == 'email' and 'print_mail_to_link' in val:
            em = re.search(r"'([^']+)','([^']+)'", val)
            if em:
                val = f"{em.group(1)}@{em.group(2)}"

        props[canon] = val

    return props


def extract_destinations(content):
    """Extract sub-destination links from the content."""
    destinations = []
    # Look for links in the Destinations section
    dest_section = extract_between(
        content, r"<h2>Destinations</h2>", r"(?:<h2>|<img[^>]*linea)"
    )
    if dest_section:
        for m in re.finditer(
            r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', dest_section, re.IGNORECASE
        ):
            href, text = m.group(1), strip_tags(m.group(2)).strip()
            if text and "addNew" not in href and "Add" not in text:
                href = re.sub(r"https?://(?:www\.)?world66\.com", "", href)
                # Flatten sub-region paths
                for subregion in SUBREGIONS_TO_FLATTEN:
                    href = href.replace("/" + subregion + "/", "/" + subregion.split("/")[0] + "/")
                destinations.append({"name": text, "path": href})
    return destinations


def flatten_subregion_path(parts):
    """Remove sub-region segments from the path.

    e.g. ['asia', 'middleeast', 'turkey', 'istanbul'] -> ['asia', 'turkey', 'istanbul']
    Returns (new_parts, old_path_or_None) where old_path is set if a redirect is needed.
    """
    if len(parts) < 2:
        return parts, None
    prefix = parts[0] + "/" + parts[1]
    if prefix in SUBREGIONS_TO_FLATTEN:
        if len(parts) == 2:
            # This is the sub-region page itself (e.g. asia/middleeast) — skip it
            return None, None
        old_path = "/".join(parts)
        new_parts = [parts[0]] + parts[2:]
        return new_parts, old_path
    return parts, None


def extract_path_info(filepath):
    """Extract geographic hierarchy from the file path."""
    rel_path = os.path.relpath(filepath, RAW_DIR)
    parts = rel_path.replace(".html", "").split(os.sep)
    return parts


def process_file(filepath):
    """Process a single raw HTML file into clean Markdown."""
    try:
        with open(filepath, "rb") as f:
            raw = f.read()
    except Exception:
        return None

    for encoding in ["utf-8", "cp1252", "latin-1"]:
        try:
            html = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        return None

    # Fix common mojibake from cp1252 content served as utf-8
    mojibake_fixes = {
        "\u00e2\u0080\u0099": "\u2019",  # â€™ -> '
        "\u00e2\u0080\u009c": "\u201c",  # â€œ -> "
        "\u00e2\u0080\u009d": "\u201d",  # â€ -> "
        "\u00e2\u0080\u0093": "\u2013",  # â€" -> –
        "\u00e2\u0080\u0094": "\u2014",  # â€" -> —
        "\u00e2\u0080\u00a6": "\u2026",  # â€¦ -> …
        "\u00c3\u00a9": "\u00e9",  # Ã© -> é
        "\u00c3\u00a8": "\u00e8",  # Ã¨ -> è
        "\u00c3\u00bc": "\u00fc",  # Ã¼ -> ü
        "\u00c3\u00b6": "\u00f6",  # Ã¶ -> ö
        "\u00c3\u00a4": "\u00e4",  # Ã¤ -> ä
        "\u00c3\u00b1": "\u00f1",  # Ã± -> ñ
    }
    for bad, good in mojibake_fixes.items():
        html = html.replace(bad, good)

    # Extract title
    title = extract_title(html)

    # Extract main content area
    main_content = extract_main_content(html)
    if not main_content:
        return None

    # Extract sub-destinations before cleaning
    destinations = extract_destinations(main_content)

    # Extract structured properties (from full HTML, not just main content)
    properties = extract_properties(html)

    # Get h1 before stripping
    h1 = extract_h1(main_content)

    # Convert to clean markdown
    body = strip_tags(main_content)

    # #8: Skip spam pages (strip_tags returns "" for detected spam)
    if body == "":
        return None

    # Build the final markdown
    path_parts = extract_path_info(filepath)

    # #2: Strip world/ prefix — it's a mirror, use as fallback
    is_world_mirror = False
    if path_parts and path_parts[0] == "world":
        path_parts = path_parts[1:]
        is_world_mirror = True
        if not path_parts:
            return None  # world/ itself, skip

    # #8: Skip junk filenames (random strings, placeholders)
    # Only check the leaf segment, and not for top-level pages (continents)
    if len(path_parts) > 1:
        last_part_check = path_parts[-1]
        if len(last_part_check) > 15 and not any(c in last_part_check for c in "_- "):
            return None  # Random string like "fhBrsdPfsB" or "eaczkqugztsvdfqxig"

    # #5: Flatten sub-regions (asia/middleeast/turkey -> asia/turkey)
    path_parts, old_path = flatten_subregion_path(path_parts)
    if path_parts is None:
        return None  # Sub-region page itself, skip

    breadcrumb = " > ".join(p.replace("_", " ").title() for p in path_parts)

    lines = []

    # Determine type — includes normalized, legacy, and misclassified section names
    SECTION_SLUGS = {
        "sights", "eating_out", "eatingout", "eating_out_intro",
        "getting_there", "gettingthere",
        "getting_around", "gettingaround",
        "practical_informat", "practicalinformat", "practicalthings", "practicaladdresses",
        "things_to_do", "thingstodo",
        "day_trips", "daytrips", "day_trips_intro",
        "shopping", "beaches", "museums",
        "nightlife_and_ente", "nightlife", "nightlifeandente",
        "bars_and_cafes", "barsandcafes",
        "festivals", "when_to_go", "top_5_must_dos", "activities",
        "books", "books_1", "books_2",
        "people", "budget_travel_idea", "family_travel_idea",
        "tours_and_excursio", "toursandexcursions",
        "travel_guide", "7_day_itinerary",
        "about", "health", "food", "history", "restaurants",
        "usefulladdresses", "drugs",
        "webcams", "webcams__360_degr",
        "aperfectdayin",
    }
    last_part = path_parts[-1] if path_parts else ""
    # Check any ancestor — POIs can be nested: .../sights/kingschapel
    is_under_section = any(p in SECTION_SLUGS for p in path_parts[:-1])

    if is_under_section:
        page_type = "poi"
        # Flatten nested section subdirs: .../sights/tombs/tomb.md -> .../sights/tomb.md
        # Keep only the first section ancestor and the POI name
        new_parts = []
        found_section = False
        for p in path_parts[:-1]:
            if p in SECTION_SLUGS and not found_section:
                found_section = True
                new_parts.append(p)
            elif not found_section:
                new_parts.append(p)
            # Skip any parts between the section and the POI
        new_parts.append(path_parts[-1])
        path_parts = new_parts
    elif last_part in SECTION_SLUGS:
        page_type = "section"
    else:
        page_type = "location"

    # Frontmatter
    page_title = h1 or title or breadcrumb
    # Strip "Travel Guide" from titles
    for suffix in [" Travel Guide", " travel guide", " travelguide"]:
        if page_title.endswith(suffix):
            page_title = page_title[:-len(suffix)].strip()

    # Strip the h1 and breadcrumb from body — template renders those
    body = re.sub(r"^# " + re.escape(page_title) + r"\s*\n*", "", body)
    body = re.sub(r"^\*[^*]+\*\s*\n*", "", body)
    # Always strip inline Destinations sections — the template renders these dynamically
    body = re.sub(r"\n?## Destinations\s*\n.*", "", body, flags=re.DOTALL)
    body = re.sub(r"\n?## Top Destinations.*?\n.*", "", body, flags=re.DOTALL)
    body = re.sub(r"\n?\*\*Show all destinations.*", "", body, flags=re.DOTALL | re.IGNORECASE)
    # Strip the raw property block text from body (we have it in frontmatter now)
    body = re.sub(r"[A-Za-z'\s]+ facts:\s*", "", body)
    body = re.sub(r"World66 rating:.*", "", body)
    body = re.sub(r"Rate now:.*", "", body)
    body = body.strip()

    # Skip POIs with no real content (but always keep locations and sections
    # so the directory structure and titles are preserved)
    if len(body) < 50 and page_type == "poi" and not properties:
        return None

    meta = {"title": page_title, "type": page_type}
    for key, val in sorted(properties.items()):
        meta[key] = val
    post = frontmatter.Post(body, **meta)
    markdown = frontmatter.dumps(post, sort_keys=False) + "\n"

    # Write output — use flattened path
    rel_path = "/".join(path_parts) + ".md"
    out_path = os.path.join(CONTENT_DIR, rel_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Write logic:
    # - world/ mirror: only write if file doesn't exist or is smaller
    # - sub-region merge: append new body to existing
    # - normal: write
    if os.path.exists(out_path):
        existing_size = os.path.getsize(out_path)
        if is_world_mirror:
            # Only overwrite if the mirror version is larger
            if len(markdown) <= existing_size:
                return None
        elif old_path:
            # Merging flattened sub-region — append unique body
            existing = open(out_path, "r", encoding="utf-8").read()
            if body and body not in existing:
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write("\n" + body + "\n")
                return {"title": page_title, "path": rel_path, "old_path": old_path,
                        "destinations": 0, "size": len(markdown)}
            return None

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return {
        "title": page_title,
        "path": rel_path,
        "old_path": old_path,
        "destinations": len(destinations),
        "size": len(markdown),
    }


def run_extraction():
    """Process all downloaded HTML files."""
    if not os.path.exists(RAW_DIR):
        print(f"Error: Raw directory not found: {RAW_DIR}")
        print("Run download_pages.py first.")
        sys.exit(1)

    os.makedirs(CONTENT_DIR, exist_ok=True)

    html_files = []
    for root, dirs, files in os.walk(RAW_DIR):
        for f in files:
            if f.endswith(".html"):
                html_files.append(os.path.join(root, f))

    print(f"Found {len(html_files)} HTML files to process")

    index = []
    redirects = {}
    processed = 0
    skipped = 0

    for filepath in sorted(html_files):
        result = process_file(filepath)
        if result:
            index.append(result)
            processed += 1
            # Collect redirects from flattened sub-regions
            old_path = result.get("old_path")
            if old_path:
                new_path = result["path"].replace(".md", "")
                old_clean = old_path.replace(".html", "")
                redirects[old_clean] = new_path
        else:
            skipped += 1

        if (processed + skipped) % 500 == 0:
            print(f"  Processed: {processed}, Skipped: {skipped}")

    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)

    if redirects:
        with open(REDIRECTS_FILE, "w") as f:
            json.dump(redirects, f, indent=2)
        print(f"  Redirects: {len(redirects)} saved to {REDIRECTS_FILE}")

    print(f"\nDone!")
    print(f"  Extracted: {processed} pages")
    print(f"  Skipped: {skipped} pages")
    print(f"  Index: {INDEX_FILE}")
    print(f"  Content: {CONTENT_DIR}/")


if __name__ == "__main__":
    run_extraction()
