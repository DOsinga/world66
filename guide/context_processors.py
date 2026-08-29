from django.conf import settings

from .models import load_continents


def continents(request):
    """Make continents available in all templates."""
    return {"continents": load_continents()}


def gtm_container_id(request):
    """Make the Google Tag Manager container ID available in all templates."""
    return {"gtm_container_id": settings.GTM_CONTAINER_ID}
