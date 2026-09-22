"""The preview toggle.

The concierge is not finished, and the site is public. Rather than ship it to
everybody, a hidden page hands out a signed cookie; visitors without that
cookie never receive the overlay markup at all, and the chat endpoint they
would have talked to returns 404 for them too.

This works because Cloudflare does not cache our HTML (`cf-cache-status:
DYNAMIC`). If HTML caching is ever turned on, this needs `Vary: Cookie` or a
bypass rule, or the first previewer's page would be served to everybody.
"""

from django.conf import settings
from django.core import signing

COOKIE_NAME = "w66_concierge"
COOKIE_SALT = "concierge-preview"
COOKIE_MAX_AGE = 60 * 60 * 24 * 90


def preview_key():
    """The shared secret that unlocks the preview, or "" when unset.

    Lives in the environment because this repository is public.
    """
    return (getattr(settings, "CONCIERGE_PREVIEW_KEY", "") or "").strip()


def make_token():
    return signing.dumps("on", salt=COOKIE_SALT)


def is_enabled(request):
    token = request.COOKIES.get(COOKIE_NAME, "")
    if not token:
        return False
    try:
        value = signing.loads(token, salt=COOKIE_SALT, max_age=COOKIE_MAX_AGE)
    except signing.BadSignature:
        return False
    return value == "on"
