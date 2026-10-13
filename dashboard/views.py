
from django.shortcuts import render


def home(request):
    context = {
        "project_name": "Fleet Management and Car Rental System",
        "total_vehicles": 0,
        "available_vehicles": 0,
        "active_bookings": 0,
        "total_customers": 0,
    }

    return render(request, "dashboard/home.html", context)
