from django.apps import AppConfig


class GuideConfig(AppConfig):
    name = "guide"

    def ready(self):
        import threading
        def warm():
            try:
                from .models import load_featured_cities, load_story_pois, load_continents
                load_featured_cities()
                load_story_pois()
                load_continents()
            except Exception:
                pass
        threading.Thread(target=warm, daemon=True).start()
