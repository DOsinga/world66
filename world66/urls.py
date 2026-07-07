from django.urls import include, path, re_path
from django.views.generic import RedirectView

from guide import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about", views.about, name="about"),
    path("search", views.search, name="search"),
    path("api/search", views.search_api, name="search_api"),
    path("tags/<str:tag>", views.tag_index, name="tag_index"),
    path("widgets/", views.widgets, name="widgets"),
    path("widgets/globe-explore", views.widget_globe_explore, name="widget_globe_explore"),
    path("widgets/photo-map", views.widget_photo_map, name="widget_photo_map"),
    path("content-image/<path:path>", views.content_image, name="content_image"),
    path("content-audio/<path:path>", views.content_audio, name="content_audio"),
    path("api/route", views.tour_route, name="tour_route"),
    path("tour/<path:path>", views.tour_view, name="tour"),
    path("review", views.review, name="review"),
    path("explore", views.map_explore_world, name="map_explore_world"),
    path("explore/<path:path>", views.map_explore, name="map_explore"),
    path("api/explore", views.api_explore_world, name="api_explore_world"),
    path("api/explore/<path:path>", views.api_explore, name="api_explore"),
    path("api/page-content/<path:path>", views.api_page_content, name="api_page_content"),
    path("passport/", include("passport_app.urls")),
    path("regions", RedirectView.as_view(url="/regions/", permanent=False)),
    path("regions/", include("regions_app.urls")),
    re_path(r"^(?P<revision>[0-9a-fA-F]{7,40})/?$", views.home_at_revision, name="home_at_revision"),
    re_path(r"^(?P<revision>[0-9a-fA-F]{7,40})/content-image/(?P<path>.+)$", views.content_image_at_revision, name="content_image_at_revision"),
    re_path(r"^(?P<revision>[0-9a-fA-F]{7,40})/(?P<path>.+)$", views.location_or_section_at_revision, name="location_or_section_at_revision"),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
