from .models import load_continents


def continents(request):
    """Make continents available in all templates."""
    return {"continents": load_continents()}
