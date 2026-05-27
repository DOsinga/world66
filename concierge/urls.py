from django.urls import path

from . import views

app_name = "concierge"

urlpatterns = [
    path("start", views.start, name="start"),
    path("webhook", views.twilio_webhook, name="webhook"),
    path("session/<uuid:session_id>", views.session_status, name="session_status"),
    path("session/<uuid:session_id>.json", views.session_json, name="session_json"),
]
