from django.conf import settings
from twilio.rest import Client
from twilio.request_validator import RequestValidator


def send_message(to_number, body):
    """Send a WhatsApp message via Twilio. `to_number` should be E.164."""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"
    message = client.messages.create(
        from_=settings.TWILIO_WHATSAPP_FROM,
        to=to_number,
        body=body,
    )
    return message.sid


def validate_request(request):
    """Return True if the incoming request is a genuine Twilio webhook."""
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    url = request.build_absolute_uri()
    post_data = request.POST.dict()
    signature = request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
    return validator.validate(url, post_data, signature)
