import threading
import uuid

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from guide.models import CONTENT_DIR, _load_page_from_file, load_page

from .agent import confirm_booking, run_agent
from .models import Message, NegotiationSession
from .scraper import extract_whatsapp_from_url
from .whatsapp import validate_request


def find_similar_bookable_pois(poi, limit=3):
    """Return up to `limit` other bookable POIs near `poi` (same parent directory tree)."""
    if "/" not in poi.path:
        return []
    parent_path = poi.path.rsplit("/", 1)[0]
    parent_dir = CONTENT_DIR / parent_path
    if not parent_dir.is_dir():
        return []
    similar = []
    for md_file in sorted(parent_dir.rglob("*.md")):
        if len(similar) >= limit:
            break
        rel = md_file.relative_to(CONTENT_DIR)
        parts = list(rel.parts)
        stem = parts[-1][:-3]
        url_path = "/".join(parts[:-1] + [stem]) if len(parts) > 1 else stem
        if url_path == poi.path:
            continue
        page = _load_page_from_file(md_file, url_path)
        if page and page.page_type == "poi" and page.meta.get("booking_url"):
            similar.append(page)
    return similar


def _resolve_whatsapp(poi):
    number = poi.meta.get("whatsapp", "")
    if not number:
        booking_url = poi.meta.get("booking_url", "")
        if booking_url:
            number = extract_whatsapp_from_url(booking_url)
    return number


def _create_session(provider_path, user_name, user_email, user_whatsapp, prefs, group_id=None):
    poi = load_page(provider_path)
    if not poi:
        return None
    session_prefs = dict(prefs, listed_price=poi.meta.get("price", ""))
    session = NegotiationSession.objects.create(
        provider_path=provider_path,
        provider_name=poi.title,
        provider_whatsapp=_resolve_whatsapp(poi),
        user_name=user_name,
        user_email=user_email,
        user_whatsapp=user_whatsapp,
        prefs=session_prefs,
        group_id=group_id,
    )
    threading.Thread(target=run_agent, args=(session.id,), daemon=True).start()
    return session


@require_POST
def start(request):
    provider_path = request.POST.get("provider_path", "").strip()
    user_name = request.POST.get("user_name", "").strip()
    user_email = request.POST.get("user_email", "").strip()
    user_whatsapp = request.POST.get("user_whatsapp", "").strip()
    also_contact = [p for p in request.POST.getlist("also_contact") if p != provider_path]

    prefs = {
        "dates": request.POST.get("dates", ""),
        "group_size": request.POST.get("group_size", ""),
        "target_price": request.POST.get("target_price", ""),
        "max_price": request.POST.get("max_price", ""),
        "notes": request.POST.get("notes", ""),
    }

    all_paths = [provider_path] + also_contact
    group_id = uuid.uuid4() if len(all_paths) > 1 else None

    sessions = []
    for path in all_paths:
        session = _create_session(path, user_name, user_email, user_whatsapp, prefs, group_id)
        if session:
            sessions.append(session)

    if not sessions:
        return HttpResponse("Provider not found.", status=404)

    primary = sessions[0]
    poi = load_page(provider_path)
    return render(request, "concierge/confirmation.html", {
        "session": primary,
        "provider": poi,
        "other_sessions": sessions[1:],
    })


@require_POST
def confirm_offer(request, session_id):
    session = get_object_or_404(NegotiationSession, id=session_id)
    if session.status != "pending_confirmation":
        return redirect("concierge:session_status", session_id=session_id)
    threading.Thread(target=confirm_booking, args=(session.id,), daemon=True).start()
    return redirect("concierge:session_status", session_id=session_id)


@csrf_exempt
def twilio_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    if not validate_request(request):
        return HttpResponse(status=403)

    from_number = request.POST.get("From", "").replace("whatsapp:", "")
    body = request.POST.get("Body", "").strip()
    twilio_sid = request.POST.get("MessageSid", "")

    session = (
        NegotiationSession.objects.filter(
            provider_whatsapp__icontains=from_number,
            status__in=["contacting", "negotiating"],
        )
        .order_by("-created_at")
        .first()
    )

    if session:
        if not Message.objects.filter(twilio_sid=twilio_sid).exists():
            Message.objects.create(
                session=session,
                direction="inbound",
                body=body,
                twilio_sid=twilio_sid,
            )
        threading.Thread(target=run_agent, args=(session.id,), daemon=True).start()

    return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response/>', content_type="text/xml")


def session_status(request, session_id):
    session = get_object_or_404(NegotiationSession, id=session_id)
    return render(request, "concierge/session.html", {"session": session})


def session_json(request, session_id):
    session = get_object_or_404(NegotiationSession, id=session_id)
    messages = list(session.messages.values("direction", "body", "timestamp"))
    for m in messages:
        m["timestamp"] = m["timestamp"].isoformat()
    return JsonResponse({
        "status": session.status,
        "summary": session.summary,
        "proposed_offer": session.proposed_offer,
        "messages": messages,
    })
