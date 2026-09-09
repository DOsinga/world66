import json

import markdown as md
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from guide.models import CONTENT_DIR, load_page


def regions_map(request):
    return render(request, "regions_app/map.html")


@require_GET
def location_detail(request, loc_path):
    try:
        page = load_page(loc_path)
    except Exception:
        return JsonResponse({"error": "Not found"}, status=404)

    # Build image URL
    image_url = None
    image_source = None
    image_license = None
    img_file = page.meta.get("image", "")
    if img_file:
        for candidate in [
            f"{loc_path}/{img_file}",
            f"{loc_path.rsplit('/', 1)[0]}/{img_file}" if "/" in loc_path else img_file,
        ]:
            if (CONTENT_DIR / candidate).is_file():
                image_url = f"/content-image/{candidate}"
                image_source = page.meta.get("image_source")
                image_license = page.meta.get("image_license")
                break

    content_html = md.markdown(page.body, extensions=["extra"]) if page.body else ""

    return JsonResponse({
        "title": page.title,
        "image_url": image_url,
        "image_source": image_source,
        "image_license": image_license,
        "content_html": content_html,
        "path": loc_path,
    })
