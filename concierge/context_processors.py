from .agent import DISCLOSURE
from .preview import is_enabled


def concierge(request):
    if not is_enabled(request):
        return {"concierge_enabled": False}
    return {"concierge_enabled": True, "disclosure": DISCLOSURE}
