from django.urls import path

from . import views

urlpatterns = [
    path("", views.regions_map, name="regions_map"),
    path("location/<path:loc_path>/", views.location_detail, name="location_detail"),
]
