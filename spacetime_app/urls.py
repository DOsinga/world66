from django.urls import path
from . import views

urlpatterns = [
    path("", views.map_view, name="spacetime_map"),
    path("events/", views.event_list, name="spacetime_event_list"),
    path("events/<slug:slug>/", views.event_detail, name="spacetime_event_detail"),
    path("api/nearby/", views.api_nearby, name="spacetime_api_nearby"),
]
