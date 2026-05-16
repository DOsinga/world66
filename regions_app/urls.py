from django.urls import path

from . import views

urlpatterns = [
    path("", views.regions_map, name="regions_map"),
]
