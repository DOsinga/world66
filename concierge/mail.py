"""Sending mail through Resend.

One POST per message; no SDK. Everything the traveller and the operator see
is templated here — the model writes the body of the enquiry and nothing else.
"""

import json
import logging
import os
import urllib.error
import urllib.request

# Overridable so the whole send path can be exercised against a stub.
API_URL = os.environ.get("RESEND_API_URL", "https://api.resend.com/emails")
USER_AGENT = "world66-concierge/1.0 (+https://world66.ai)"
TIMEOUT = 15

logger = logging.getLogger(__name__)


def api_key():
    return (os.environ.get("RESEND_API_KEY", "") or "").strip()


def from_address():
    """The envelope sender.

    The apex domain, because that is what is verified with the mail provider
    and what DKIM signs. world66.ai publishes `p=reject` with strict alignment
    (`adkim=s`), so a From address on any subdomain would be rejected by our
    own DMARC policy even though the mail is genuinely ours.
    """
    return os.environ.get("CONCIERGE_FROM", "World66 concierge <concierge@world66.ai>")


def is_configured():
    return bool(api_key())


def send(to, subject, text, reply_to=""):
    """Send one message. Returns the provider's message id, or "" on failure."""
    payload = {
        "from": from_address(),
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            # Resend's API sits behind Cloudflare, which answers urllib's
            # default agent string with a 1010 before Resend sees the request.
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        # The reply says why — a wrong key, an unverified sender domain, a
        # rate limit. Losing it silently costs an afternoon.
        detail = err.read().decode("utf-8", "replace")[:400]
        logger.error("resend refused the message: HTTP %s %s", err.code, detail)
        return ""
    except (urllib.error.URLError, ValueError, OSError) as err:
        logger.error("could not reach resend: %s", err)
        return ""
    return str(body.get("id") or "")
