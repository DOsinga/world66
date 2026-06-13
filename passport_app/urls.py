from django.urls import path

from . import views

urlpatterns = [
    path("", views.passport_list, name="passport_list"),
    path("new", views.passport_new, name="passport_new"),
    path("<str:slug>/protect", views.passport_protect, name="passport_protect"),
    path("<str:slug>/login", views.passport_login, name="passport_login"),
    path("<str:slug>/swipe", views.passport_swipe, name="passport_swipe"),
    path("<str:slug>", views.passport_detail, name="passport_detail"),
]
