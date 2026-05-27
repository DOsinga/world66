import threading

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from guide.models import load_page

from .agent import run_agent
from .models import Message, NegotiationSession
from .scraper import extract_whatsapp_from_url
from .whatsapp import validate_request


@require_POST
def start(request):
    provider_path = request.POST.get("provider_path", "").strip()
    user_name = request.POST.get("user_name", "").strip()
    user_whatsapp = request.POST.get("user_whatsapp", "").strip()

    poi = load_page(provider_path)
    if not poi:
        return HttpResponse("Provider not found.", status=404)

    provider_whatsapp = poi.meta.get("whatsapp", "")
    if not provider_whatsapp:
        booking_url = poi.meta.get("booking_url", "")
        if booking_url:
            provider_whatsapp = extract_whatsapp_from_url(booking_url)

    prefs = {
        "dates": request.POST.get("dates", ""),
        "group_size": request.POST.get("group_size", ""),
        "listed_price": poi.meta.get("price", ""),
        "target_price": request.POST.get("target_price", ""),
        "max_price": request.POST.get("max_price", ""),
        "notes": request.POST.get("notes", ""),
    }

    session = NegotiationSession.objects.create(
        provider_path=provider_path,
        provider_name=poi.title,
        provider_whatsapp=provider_whatsapp,
        user_name=user_name,
        user_whatsapp=user_whatsapp,
        prefs=prefs,
    )

    threading.Thread(target=run_agent, args=(session.id,), daemon=True).start()

    return redirect("concierge:session_status", session_id=session.id)


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
    messages = list(
        session.messages.values("direction", "body", "timestamp")
    )
    for m in messages:
        m["timestamp"] = m["timestamp"].isoformat()
    return JsonResponse({
        "status": session.status,
        "summary": session.summary,
        "messages": messages,
    })
