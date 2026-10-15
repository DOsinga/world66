from django.urls import path

from . import views

urlpatterns = [
    path("preview", views.preview, name="concierge_preview"),
    path("chat", views.chat, name="concierge_chat"),
    path("enquiry", views.enquiry, name="concierge_enquiry"),
    path("confirm/<str:token>", views.confirm, name="concierge_confirm"),
    path("no-enquiries/<str:token>", views.no_enquiries, name="concierge_no_enquiries"),
]
