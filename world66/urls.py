from django.contrib import admin
from django.urls import path

from guide import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
