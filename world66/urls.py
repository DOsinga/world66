from django.urls import path

from guide import views

urlpatterns = [
    path("", views.home, name="home"),
    path("content-image/<path:path>", views.content_image, name="content_image"),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
