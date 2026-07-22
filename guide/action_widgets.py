"""
Site-wide "place action" widgets.

Unlike guide/overlays.py (a supplier providing extra content for one
content path), an action widget adds an action to content that already
exists, anywhere on the site — e.g. "add to trip". World66 has zero
knowledge of what a registered widget does: it renders a generic,
documented place-info element (see ACTION_WIDGETS.md) and includes the
widget's own script; everything else — UI, auth, API calls — is the
widget's own problem to solve on its own domain.
"""

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from django.conf import settings

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(settings.BASE_DIR) / "action_widgets.yaml"

# Session key used to persist a visitor's choice of which registered
# widgets to show, across requests (mirrors overlays.SESSION_KEY).
SESSION_KEY = "disabled_action_widgets"


@lru_cache(maxsize=1)
def registered_widgets():
    """Load action_widgets.yaml once per process. Each entry: {name, script_url, display_name}."""
    if not REGISTRY_PATH.is_file():
        return []
    try:
        data = yaml.safe_load(REGISTRY_PATH.read_text()) or []
    except (OSError, yaml.YAMLError):
        logger.warning("Could not read action widget registry at %s", REGISTRY_PATH)
        return []
    if not isinstance(data, list):
        return []
    return [
        {"name": e["name"], "script_url": e["script_url"], "display_name": e.get("display_name") or e["name"]}
        for e in data
        if isinstance(e, dict) and e.get("name") and e.get("script_url")
    ]


def active_widgets(disabled_names):
    """registered_widgets(), minus whichever names this visitor has turned off."""
    disabled = frozenset(disabled_names or ())
    return [w for w in registered_widgets() if w["name"] not in disabled]
