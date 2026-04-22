from django.urls import path

from guide import feedback, views

urlpatterns = [
    path("", views.home, name="home"),
    path("search", views.search, name="search"),
    path("api/search", views.search_api, name="search_api"),
    path("tags/<str:tag>", views.tag_index, name="tag_index"),
    path("content-image/<path:path>", views.content_image, name="content_image"),
    path("review", views.review, name="review"),
    path("api/feedback", feedback.submit_feedback, name="submit_feedback"),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
