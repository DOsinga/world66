import re
import subprocess

from django.conf import settings
from django.shortcuts import redirect


HASH_PREFIX_RE = re.compile(r"^/[0-9a-fA-F]{7,40}(?:/|$)")
STAGING_SKIP_PREFIXES = (
    "/about",
    "/api/",
    "/content-image/",
    "/media/",
    "/passport/",
    "/regions",
    "/review",
    "/search",
    "/static/",
    "/tags/",
)


def _resolve_staging_ref():
    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "--verify",
            "--short=10",
            f"{settings.STAGING_CONTENT_REF}^{{commit}}",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(settings.BASE_DIR),
    )
    if result.returncode == 0:
        return result.stdout.strip()

    fallback = subprocess.run(
        [
            "git",
            "rev-parse",
            "--verify",
            "--short=10",
            "origin/main^{commit}",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(settings.BASE_DIR),
    )
    if fallback.returncode == 0:
        return fallback.stdout.strip()
    return ""


class StagingRevisionRedirectMiddleware:
    """Redirect staging guide pages into the local main revision URL space."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":", 1)[0]
        if host in getattr(settings, "STAGING_HOSTS", set()):
            path = request.path_info
            if self._should_redirect(path):
                revision = _resolve_staging_ref()
                if revision:
                    query = f"?{request.META['QUERY_STRING']}" if request.META.get("QUERY_STRING") else ""
                    return redirect(f"/{revision}{path}{query}", permanent=False)
        return self.get_response(request)

    @staticmethod
    def _should_redirect(path):
        if path in ("", "/"):
            return False
        if HASH_PREFIX_RE.match(path):
            return False
        return not path.startswith(STAGING_SKIP_PREFIXES)
