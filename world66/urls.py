from django.urls import path

from guide import views
from guide.feedback import submit_feedback

urlpatterns = [
    path("", views.home, name="home"),
    path("search", views.search, name="search"),
    path("api/search", views.search_api, name="search_api"),
    path("api/feedback", submit_feedback, name="feedback"),
    path("tags/<str:tag>", views.tag_index, name="tag_index"),
    path("content-image/<path:path>", views.content_image, name="content_image"),
    path("review", views.review, name="review"),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
