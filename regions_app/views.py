from django.shortcuts import render


def regions_map(request):
    return render(request, "regions_app/map.html")
