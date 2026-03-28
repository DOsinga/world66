from django.urls import path

from guide import views

urlpatterns = [
    path("", views.home, name="home"),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
