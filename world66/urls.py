from django.urls import include, path

from guide import views
from plans_app.views import api_plan_create, api_plan_add_pois, api_research_submit

urlpatterns = [
    path("", views.home, name="home"),
    path("search", views.search, name="search"),
    path("api/search", views.search_api, name="search_api"),
    path("api/plans/create", api_plan_create, name="api_plan_create"),
    path("api/plan/add-pois", api_plan_add_pois, name="api_plan_add_pois"),
    path("api/research/submit", api_research_submit, name="api_research_submit"),
    path("tags/<str:tag>", views.tag_index, name="tag_index"),
    path("content-image/<path:path>", views.content_image, name="content_image"),
    path("review", views.review, name="review"),
    path("plans/", include("plans_app.urls")),
    path("<path:path>", views.location_or_section, name="location_or_section"),
]
