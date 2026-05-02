from django.urls import include, path

from guide import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search", views.search, name="search"),
    path("api/search", views.search_api, name="search_api"),
    path("tags/<str:tag>", views.tag_index, name="tag_index"),
    path("content-image/<path:path>", views.content_image, name="content_image"),
    path("review", views.review, name="review"),
    path("join", views.join, name="join"),
    path("auth/signup/<slug:slug>/", views.auth_signup, name="auth_signup"),
    path("auth/login/<slug:slug>/", views.auth_login, name="auth_login"),
    path("auth/logout/", views.auth_logout, name="auth_logout"),
    path("plans/", include("plans_app.urls")),
    path("timespace/", include("spacetime_app.urls")),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
