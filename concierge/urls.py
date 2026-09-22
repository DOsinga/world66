from django.urls import path

from . import views

urlpatterns = [
    path("preview", views.preview, name="concierge_preview"),
    path("chat", views.chat, name="concierge_chat"),
]
