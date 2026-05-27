from django.urls import include, path
from django.views.generic import RedirectView

from guide import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search", views.search, name="search"),
    path("api/search", views.search_api, name="search_api"),
    path("tags/<str:tag>", views.tag_index, name="tag_index"),
    path("content-image/<path:path>", views.content_image, name="content_image"),
    path("review", views.review, name="review"),
    path("passport/", include("passport_app.urls")),
    path("regions", RedirectView.as_view(url="/regions/", permanent=False)),
    path("regions/", include("regions_app.urls")),
    path("concierge/", include("concierge.urls")),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
