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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
CONTENT_DIR = os.path.join(SCRIPT_DIR, "content")
INDEX_FILE = os.path.join(SCRIPT_DIR, "site_index.json")


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
        # Skip image/upload/change links
        if any(
            x in href.lower()
            for x in [
                "imagechange",
                "imageupload",
                "image/change",
                "image/upload",
                "modify",
            ]
        ):
            return link_text
        # Clean world66 URLs to relative
        href = re.sub(r"https?://(?:www\.)?world66\.com", "", href)
        if href and link_text.strip():
            return f"[{link_text.strip()}]({href})"
        return link_text

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

    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)  # Collapse horizontal whitespace
    text = re.sub(r"\n[ \t]+", "\n", text)  # Remove leading whitespace on lines
    text = re.sub(r"[ \t]+\n", "\n", text)  # Remove trailing whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse multiple blank lines

    return text.strip()


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
                destinations.append({"name": text, "path": href})
    return destinations


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

    # Get h1 before stripping
    h1 = extract_h1(main_content)

    # Convert to clean markdown
    body = strip_tags(main_content)

    if len(body) < 50:
        return None

    # Build the final markdown
    path_parts = extract_path_info(filepath)
    breadcrumb = " > ".join(p.replace("_", " ").title() for p in path_parts)

    lines = []
    # Use h1 if available, otherwise title, otherwise breadcrumb
    page_title = h1 or title or breadcrumb
    lines.append(f"# {page_title}")
    lines.append("")
    lines.append(f"*{breadcrumb}*")
    lines.append("")

    # Skip the first h1 if it duplicates our title
    body = re.sub(r"^# " + re.escape(page_title) + r"\s*\n*", "", body)
    # If we have extracted destinations, remove the inline Destinations section
    # to avoid duplication
    if destinations:
        body = re.sub(r"\n## Destinations\n.*", "", body, flags=re.DOTALL)
    body = body.strip()

    if body:
        lines.append(body)
        lines.append("")

    # Add clean destinations section if found
    if destinations:
        lines.append("## Destinations")
        lines.append("")
        for dest in destinations:
            lines.append(f"- [{dest['name']}]({dest['path']})")
        lines.append("")

    markdown = "\n".join(lines)

    # Write output
    rel_path = os.path.relpath(filepath, RAW_DIR).replace(".html", ".md")
    out_path = os.path.join(CONTENT_DIR, rel_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return {
        "title": page_title,
        "path": rel_path,
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
    processed = 0
    skipped = 0

    for filepath in sorted(html_files):
        result = process_file(filepath)
        if result:
            index.append(result)
            processed += 1
        else:
            skipped += 1

        if (processed + skipped) % 500 == 0:
            print(f"  Processed: {processed}, Skipped: {skipped}")

    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)

    print(f"\nDone!")
    print(f"  Extracted: {processed} pages")
    print(f"  Skipped: {skipped} pages")
    print(f"  Index: {INDEX_FILE}")
    print(f"  Content: {CONTENT_DIR}/")


if __name__ == "__main__":
    run_extraction()
