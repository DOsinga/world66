import json

from django.core.cache import cache
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import agent
from .preview import COOKIE_MAX_AGE, COOKIE_NAME, is_enabled, make_token, preview_key

MAX_MESSAGES = 40
MAX_MESSAGE_CHARS = 2000
CHAT_RATE = 60          # turns
CHAT_WINDOW = 60 * 60   # per hour, per address


def _client_ip(request):
    """The address Django saw.

    Not X-Forwarded-For: a client can send whatever it likes in that header,
    which would let one caller spread its turns over as many buckets as it
    cares to invent.
    """
    return request.META.get("REMOTE_ADDR", "")


def _rate_limited(key):
    cache.add(key, 0, CHAT_WINDOW)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, CHAT_WINDOW)
        count = 1
    return count > CHAT_RATE


def preview(request):
    """The hidden unlock page: /concierge/preview?key=…

    Wrong key, or no key configured, and this page does not exist as far as
    the visitor can tell.
    """
    key = preview_key()
    if not key:
        raise Http404
    if request.GET.get("off"):
        response = redirect("/")
        response.delete_cookie(COOKIE_NAME)
        return response
    if request.GET.get("key", "") != key:
        raise Http404
    response = render(request, "concierge/preview.html", {"disclosure": agent.DISCLOSURE})
    response.set_cookie(
        COOKIE_NAME, make_token(),
        max_age=COOKIE_MAX_AGE, samesite="Lax", secure=request.is_secure(), httponly=True,
    )
    return response


@require_POST
def chat(request):
    # The gate is on the endpoint too, not only on the markup: without this it
    # is an open door to a metered model.
    if not is_enabled(request):
        raise Http404
    if not agent.is_configured():
        return JsonResponse(
            {"error": "The concierge is not configured on this server."}, status=503
        )
    if _rate_limited(f"concierge-chat:{_client_ip(request)}"):
        return JsonResponse(
            {"error": "That is a lot of questions for one hour — try again later."},
            status=429,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Malformed request."}, status=400)

    history = []
    for item in (payload.get("messages") or [])[-MAX_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content") or "")[:MAX_MESSAGE_CHARS]
        if role in ("user", "assistant") and content.strip():
            history.append({"role": role, "content": content})
    if not history or history[-1]["role"] != "user":
        return JsonResponse({"error": "Nothing to reply to."}, status=400)

    try:
        text, brief = agent.reply(history, str(payload.get("path") or "")[:200])
    except Exception:
        return JsonResponse(
            {"error": "The concierge could not answer just now. Please try again."},
            status=502,
        )
    return JsonResponse({"reply": text, "brief": brief})
