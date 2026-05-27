import re
import urllib.request

# Patterns that reveal a WhatsApp number in a URL or text
_WA_URL_RE = re.compile(
    r"(?:wa\.me|api\.whatsapp\.com/send)[/\?].*?(\+?\d[\d\s\-]{7,})"
)
_WA_TEXT_RE = re.compile(
    r"whatsapp[:\s]+(\+?\d[\d\s\-]{7,})", re.IGNORECASE
)
_TEL_RE = re.compile(r'href=["\']tel:(\+?\d[\d\s\-]{7,})["\']', re.IGNORECASE)


def _normalise(number):
    """Strip whitespace/dashes and ensure + prefix."""
    number = re.sub(r"[\s\-]", "", number)
    if not number.startswith("+"):
        number = "+" + number
    return number


def extract_whatsapp_from_url(url):
    """Fetch `url` and return the first WhatsApp number found, or ''."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (world66-concierge/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""

    for pattern in (_WA_URL_RE, _WA_TEXT_RE, _TEL_RE):
        m = pattern.search(html)
        if m:
            return _normalise(m.group(1))

    return ""
