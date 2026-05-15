from django.urls import path

from . import views

urlpatterns = [
    path("", views.passport_list, name="passport_list"),
    path("new", views.passport_new, name="passport_new"),
    path("<str:slug>/protect", views.passport_protect, name="passport_protect"),
    path("<str:slug>/login", views.passport_login, name="passport_login"),
    path("<str:slug>/experiences", views.passport_experiences, name="passport_experiences"),
    path("<str:slug>/photos", views.passport_photos, name="passport_photos"),
    path("<str:slug>/places", views.passport_places, name="passport_places"),
    path("<str:slug>/scenarios", views.passport_scenarios, name="passport_scenarios"),
    path("<str:slug>/photo/<str:filename>", views.passport_photo, name="passport_photo"),
    path("<str:slug>", views.passport_detail, name="passport_detail"),
]
