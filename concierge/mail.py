"""Sending mail through Resend.

One POST per message; no SDK. Everything the traveller and the operator see
is templated here — the model writes the body of the enquiry and nothing else.
"""

import json
import os
import urllib.error
import urllib.request

# Overridable so the whole send path can be exercised against a stub.
API_URL = os.environ.get("RESEND_API_URL", "https://api.resend.com/emails")
TIMEOUT = 15


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
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError):
        return ""
    return str(body.get("id") or "")
