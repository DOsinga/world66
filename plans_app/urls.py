from django.urls import path
from . import views

urlpatterns = [
    path("draft-poi/<path:poi_path>/", views.draft_poi_detail, name="draft_poi_detail"),
    path("", views.plan_list, name="plan_list"),
    path("new/", views.plan_new, name="plan_new"),
    path("join/", views.plan_join, name="plan_join"),
    path("<slug:slug>/created/", views.plan_created, name="plan_created"),
    path("<slug:slug>/edit/", views.plan_edit, name="plan_edit"),
    path("<slug:slug>/add/", views.plan_poi_add, name="plan_poi_add"),
    path("<slug:slug>/<slug:city_slug>/add/", views.plan_poi_add, name="plan_poi_add_city"),
    path("<slug:slug>/<slug:city_slug>/remove/", views.plan_poi_remove, name="plan_poi_remove"),
    path("<slug:slug>/<slug:city_slug>/note/", views.plan_note_edit, name="plan_note_edit"),
    path("<slug:slug>/<slug:city_slug>/", views.plan_stop, name="plan_stop"),
    path("<slug:slug>/", views.plan_detail, name="plan_detail"),
]
