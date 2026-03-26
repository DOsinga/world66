from django.contrib import admin

from .models import Location, Section


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    fields = ("section_type", "title", "slug")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "path", "depth", "parent")
    list_filter = ("depth",)
    search_fields = ("name", "path")
    inlines = [SectionInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "section_type")
    list_filter = ("section_type",)
    search_fields = ("title", "location__name")
