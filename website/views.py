
from django.db.models import Q
from django.shortcuts import render

from fleet.models import Vehicle


def home(request):
    """
    Public homepage displaying vehicles from the existing fleet database.
    """
    vehicles = Vehicle.objects.filter(
        status="available"
    ).order_by("registration_number")

    search_query = request.GET.get("q", "").strip()

    if search_query:
        vehicles = vehicles.filter(
            Q(make__icontains=search_query)
            | Q(model__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    context = {
        "vehicles": vehicles,
        "search_query": search_query,
    }

    return render(request, "website/home.html", context)


def vehicle_list(request):
    """
    Public vehicle catalogue with basic search and filtering.
    """
    vehicles = Vehicle.objects.filter(
        status="available"
    ).order_by("make", "model")

    search_query = request.GET.get("q", "").strip()

    if search_query:
        vehicles = vehicles.filter(
            Q(make__icontains=search_query)
            | Q(model__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    context = {
        "vehicles": vehicles,
        "search_query": search_query,
    }

    return render(request, "website/vehicle_list.html", context)