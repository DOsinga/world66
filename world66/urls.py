from django.urls import path

from guide import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search", views.search, name="search"),
    path("api/search", views.search_api, name="search_api"),
    path("tags/<str:tag>", views.tag_index, name="tag_index"),
    path("content-image/<path:path>", views.content_image, name="content_image"),
    path("review", views.review, name="review"),
    path("auth/signup/<slug:slug>/", views.auth_signup, name="auth_signup"),
    path("auth/login/<slug:slug>/", views.auth_login, name="auth_login"),
    path("auth/logout/", views.auth_logout, name="auth_logout"),
    path("plans/", views.plan_list, name="plan_list"),
    path("plans/new/", views.plan_new, name="plan_new"),
    path("plans/join/", views.plan_join, name="plan_join"),
    path("plans/<slug:slug>/created/", views.plan_created, name="plan_created"),
    path("plans/<slug:slug>/", views.plan_detail, name="plan_detail"),
    path("plans/<slug:slug>/edit/", views.plan_edit, name="plan_edit"),
    path("plans/<slug:slug>/add/", views.plan_poi_add, name="plan_poi_add"),
    path("plans/<slug:slug>/<slug:city_slug>/add/", views.plan_poi_add, name="plan_poi_add_city"),
    path("plans/<slug:slug>/<slug:city_slug>/remove/", views.plan_poi_remove, name="plan_poi_remove"),
    path("plans/<slug:slug>/<slug:city_slug>/note/", views.plan_note_edit, name="plan_note_edit"),
    path("plans/<slug:slug>/<slug:city_slug>/", views.plan_stop, name="plan_stop"),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
