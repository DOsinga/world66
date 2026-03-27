import markdown as md
from django.http import Http404
from django.shortcuts import render

from .models import load_continents, load_location, load_section


def home(request):
    continents = load_continents()
    return render(request, "guide/home.html", {"continents": continents})


def location_or_section(request, path):
    path = path.strip("/")

    # Try as a location first
    location = load_location(path)
    if location:
        return location_view(request, location)

    # Try as a section (last segment is section slug)
    if "/" in path:
        loc_path, section_slug = path.rsplit("/", 1)
        location = load_location(loc_path)
        if location:
            section = load_section(loc_path, section_slug)
            if section:
                return section_view(request, location, section)

    raise Http404


def location_view(request, location):
    children = location.children()
    sections = location.sections()
    body_html = md.markdown(location.body) if location.body else ""

    return render(request, "guide/location.html", {
        "location": location,
        "children": children,
        "sections": sections,
        "body_html": body_html,
        "breadcrumbs": location.breadcrumbs(),
    })


def section_view(request, location, section):
    body_html = md.markdown(section.body) if section.body else ""
    all_sections = location.sections()

    return render(request, "guide/section.html", {
        "location": location,
        "section": section,
        "all_sections": all_sections,
        "body_html": body_html,
        "breadcrumbs": location.breadcrumbs(),
    })
