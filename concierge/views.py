import json

from django.core import signing
from django.core.cache import cache
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from guide import github
from guide.models import load_page

from . import agent, mail, outreach
from .preview import COOKIE_MAX_AGE, COOKIE_NAME, is_enabled, make_token, preview_key

MAX_MESSAGES = 40
MAX_MESSAGE_CHARS = 2000
CHAT_RATE = 60          # turns
CHAT_WINDOW = 60 * 60   # per hour, per address

# Enquiries reach real businesses, so they are counted far more tightly than
# chat turns, and against the address as well as the caller.
ENQUIRY_RATE = 5
ENQUIRY_WINDOW = 60 * 60 * 24


def _client_ip(request):
    """The address Django saw.

    Not X-Forwarded-For: a client can send whatever it likes in that header,
    which would let one caller spread its turns over as many buckets as it
    cares to invent.
    """
    return request.META.get("REMOTE_ADDR", "")


def _rate_limited(key, limit=CHAT_RATE, window=CHAT_WINDOW):
    cache.add(key, 0, window)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        count = 1
    return count > limit


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
        text, extras = agent.reply(history, str(payload.get("path") or "")[:200])
    except Exception:
        return JsonResponse(
            {"error": "The concierge could not answer just now. Please try again."},
            status=502,
        )
    return JsonResponse({
        "reply": text,
        "brief": extras.get("brief"),
        "draft": extras.get("draft"),
    })


@require_POST
def enquiry(request):
    """Take the traveller's details and email them a confirmation link.

    This is as far as an unverified address gets. Everything the operator will
    read is already fixed in the signed draft; all this step adds is who is
    asking and where the replies should go.
    """
    if not is_enabled(request):
        raise Http404
    if not mail.is_configured():
        return JsonResponse(
            {"error": "Sending is not configured on this server."}, status=503
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Malformed request."}, status=400)

    # A field no human sees and no human fills in.
    if str(payload.get("website") or "").strip():
        return JsonResponse({"ok": True, "message": "Check your inbox."})

    draft = outreach.load_draft(payload.get("token"))
    if not draft:
        return JsonResponse(
            {"error": "That draft has expired. Ask the concierge to write it again."},
            status=400,
        )

    name = str(payload.get("name") or "").strip()[:outreach.MAX_NAME]
    email = str(payload.get("email") or "").strip()[:200]
    if not name or not outreach.valid_email(email):
        return JsonResponse({"error": "We need your name and a valid email address."}, status=400)

    if _rate_limited(f"concierge-enq-ip:{_client_ip(request)}", ENQUIRY_RATE, ENQUIRY_WINDOW):
        return JsonResponse(
            {"error": "That is a lot of enquiries for one day. Try again tomorrow."},
            status=429,
        )
    if _rate_limited(f"concierge-enq-to:{email.lower()}", ENQUIRY_RATE, ENQUIRY_WINDOW):
        return JsonResponse(
            {"error": "That is a lot of enquiries for one day. Try again tomorrow."},
            status=429,
        )

    providers, _ = outreach.resolve_providers(draft.get("providers"))
    if not providers:
        return JsonResponse(
            {"error": "Those operators can no longer be reached by email."}, status=400
        )

    traveller = {"name": name, "email": email}
    token = outreach.sign_confirmation({"draft": draft, "traveller": traveller})
    confirm_url = request.build_absolute_uri(f"/concierge/confirm/{token}")
    subject, body = outreach.build_confirmation(draft, providers, traveller, confirm_url)
    if not mail.send(email, subject, body):
        return JsonResponse(
            {"error": "We could not send the confirmation. Please try again."}, status=502
        )

    return JsonResponse({
        "ok": True,
        "message": (
            f"Sent a confirmation to {email}. Open it and confirm, and your "
            f"enquiry goes to {len(providers)} operator"
            f"{'s' if len(providers) != 1 else ''}."
        ),
    })


def confirm(request, token):
    """The link from the traveller's inbox.

    A GET only shows what is about to happen: mail clients and scanners follow
    links on their own, and a fetch by a spam filter must not send anything.
    The POST behind the button is what releases it.
    """
    payload = outreach.load_confirmation(token)
    if not payload:
        return render(request, "concierge/confirm.html",
                      {"expired": True}, status=400)

    draft = payload.get("draft") or {}
    traveller = payload.get("traveller") or {}
    providers, dropped = outreach.resolve_providers(draft.get("providers"))
    context = {
        "token": token,
        "draft": draft,
        "traveller": traveller,
        "providers": providers,
        "dropped": dropped,
    }

    if request.method != "POST":
        context["already"] = outreach.already_sent(token)
        return render(request, "concierge/confirm.html", context)

    if outreach.already_sent(token):
        context["already"] = True
        return render(request, "concierge/confirm.html", context)
    if not providers:
        context["dropped"] = dropped or ["those operators can no longer be reached"]
        return render(request, "concierge/confirm.html", context, status=400)
    if not mail.is_configured():
        return render(request, "concierge/confirm.html",
                      dict(context, failed=True), status=503)

    sent = []
    for provider in providers:
        page_url = request.build_absolute_uri(f"/{provider.path}")
        optout_token = signing.dumps(provider.path, salt=outreach.OPTOUT_SALT)
        optout_url = request.build_absolute_uri(f"/concierge/no-enquiries/{optout_token}")
        subject, body = outreach.build_enquiry(
            provider, draft, traveller, page_url, optout_url
        )
        message_id = mail.send(
            outreach.provider_email(provider), subject, body,
            reply_to=traveller.get("email", ""),
        )
        outreach.record(outreach.ledger_entry(provider, traveller, draft, token, message_id))
        if message_id:
            sent.append(provider)

    return render(request, "concierge/sent.html", {
        "sent": sent,
        "failed": [p for p in providers if p not in sent],
        "traveller": traveller,
    })


def no_enquiries(request, token):
    """An operator asking not to be written to again.

    There is nowhere on this server to remember that — the content is the
    database and it lives in git — so this files an issue against the repo and
    a person sets `no_enquiries` on the page.
    """
    try:
        path = signing.loads(token, salt=outreach.OPTOUT_SALT, max_age=60 * 60 * 24 * 365)
    except signing.BadSignature:
        raise Http404
    page = load_page(path)
    if not page:
        raise Http404

    filed = False
    if request.method == "POST":
        url = github.create_issue(
            f"No enquiries: {page.title}",
            f"{page.title} (`{page.path}`) asked not to receive concierge "
            f"enquiries.\n\nSet `no_enquiries: true` in the frontmatter of "
            f"`content/{page.path}.md`.",
            labels=("concierge",),
        )
        filed = True

    return render(request, "concierge/no_enquiries.html", {"page": page, "filed": filed})
