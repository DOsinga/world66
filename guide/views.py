import markdown
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import Location, Section


def home(request):
    continents = Location.objects.filter(depth=0).order_by("name")
    return render(request, "guide/home.html", {"continents": continents})


def location_or_section(request, path):
    """Unified view: try location first, then section."""
    # Try as a location
    try:
        location = Location.objects.get(path=path)
        return location_view(request, location)
    except Location.DoesNotExist:
        pass

    # Try as a section (last segment is section slug)
    parts = path.rsplit("/", 1)
    if len(parts) == 2:
        loc_path, section_slug = parts
        try:
            location = Location.objects.get(path=loc_path)
            section = Section.objects.get(location=location, slug=section_slug)
            return section_view(request, location, section)
        except (Location.DoesNotExist, Section.DoesNotExist):
            pass

    raise Http404


def location_view(request, location):
    children = location.children.order_by("name")
    sections = location.sections.all()
    body_html = markdown.markdown(location.body) if location.body else ""

    return render(request, "guide/location.html", {
        "location": location,
        "children": children,
        "sections": sections,
        "body_html": body_html,
        "breadcrumbs": location.breadcrumbs(),
    })


def section_view(request, location, section):
    body_html = markdown.markdown(section.body) if section.body else ""
    all_sections = location.sections.all()

    return render(request, "guide/section.html", {
        "location": location,
        "section": section,
        "all_sections": all_sections,
        "body_html": body_html,
        "breadcrumbs": location.breadcrumbs(),
    })
