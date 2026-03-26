from django.db import models


class Location(models.Model):
    """A place in the geographic hierarchy: continent, country, region, or city."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    path = models.CharField(max_length=1024, unique=True, db_index=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    depth = models.PositiveIntegerField(default=0)
    body = models.TextField(blank=True)
    image = models.CharField(max_length=1024, blank=True)

    class Meta:
        ordering = ["path"]

    def __str__(self):
        return self.name

    def breadcrumbs(self):
        crumbs = []
        loc = self
        while loc:
            crumbs.append((loc.name, loc.path))
            loc = loc.parent
        crumbs.reverse()
        return crumbs

    def get_absolute_url(self):
        return f"/{self.path}"


class Section(models.Model):
    """A content section for a location (sights, eating_out, etc.)."""

    SECTION_TYPES = [
        ("sights", "Sights"),
        ("eating_out", "Eating Out"),
        ("getting_there", "Getting There"),
        ("getting_around", "Getting Around"),
        ("practical_informat", "Practical Information"),
        ("things_to_do", "Things to Do"),
        ("day_trips", "Day Trips"),
        ("shopping", "Shopping"),
        ("beaches", "Beaches"),
        ("museums", "Museums"),
        ("nightlife_and_ente", "Nightlife & Entertainment"),
        ("nightlife", "Nightlife"),
        ("bars_and_cafes", "Bars & Cafes"),
        ("festivals", "Festivals"),
        ("when_to_go", "When to Go"),
        ("top_5_must_dos", "Top 5 Must Do's"),
        ("activities", "Activities"),
        ("books", "Books"),
        ("people", "People"),
        ("budget_travel_idea", "Budget Travel Ideas"),
        ("family_travel_idea", "Family Travel Ideas"),
        ("tours_and_excursio", "Tours & Excursions"),
        ("travel_guide", "Travel Guide"),
        ("7_day_itinerary", "7-Day Itinerary"),
    ]

    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="sections"
    )
    section_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    body = models.TextField(blank=True)
    image = models.CharField(max_length=1024, blank=True)

    class Meta:
        unique_together = ("location", "slug")
        ordering = ["section_type"]

    def __str__(self):
        return f"{self.location.name} - {self.title}"

    @property
    def display_name(self):
        for slug, name in self.SECTION_TYPES:
            if slug == self.section_type:
                return name
        return self.title

    def get_absolute_url(self):
        return f"/{self.location.path}/{self.slug}"
