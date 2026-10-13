
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from .models import Vehicle
from .forms import VehicleForm
from django.db.models import ProtectedError
from .models import Driver
from .forms import DriverForm
from .models import  Maintenance
from .forms import  MaintenanceForm


def vehicle_list(request):
    vehicles = Vehicle.objects.all()

    query = request.GET.get("q", "").strip()
    if query:
        vehicles = vehicles.filter(
            registration_number__icontains=query
        ) | vehicles.filter(make__icontains=query) | vehicles.filter(
            model__icontains=query
        )

    return render(
        request,
        "fleet/vehicle_list.html",
        {
            "vehicles": vehicles,
            "query": query,
        },
    )


def vehicle_create(request):
    if request.method == "POST":
        form = VehicleForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle registered successfully.")
            return redirect("fleet:vehicle_list")
    else:
        form = VehicleForm()

    return render(
        request,
        "fleet/vehicle_form.html",
        {
            "form": form,
            "page_title": "Register Vehicle",
        },
    )


def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)

    return render(
        request,
        "fleet/vehicle_detail.html",
        {"vehicle": vehicle},
    )


def vehicle_update(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)

    if request.method == "POST":
        form = VehicleForm(
            request.POST,
            request.FILES,
            instance=vehicle,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle updated successfully.")
            return redirect("fleet:vehicle_list")
    else:
        form = VehicleForm(instance=vehicle)

    return render(
        request,
        "fleet/vehicle_form.html",
        {
            "form": form,
            "vehicle": vehicle,
            "page_title": "Edit Vehicle",
        },
    )


def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)

    if request.method == "POST":
        vehicle.delete()
        messages.success(request, "Vehicle deleted successfully.")
        return redirect("fleet:vehicle_list")

    return render(
        request,
        "fleet/vehicle_confirm_delete.html",
        {"vehicle": vehicle},
    )

def driver_list(request):
    drivers = Driver.objects.all()
    query = request.GET.get("q", "").strip()

    if query:
        drivers = drivers.filter(
            first_name__icontains=query
        ) | drivers.filter(
            last_name__icontains=query
        ) | drivers.filter(
            phone__icontains=query
        ) | drivers.filter(
            licence_number__icontains=query
        )

    return render(
        request,
        "fleet/driver_list.html",
        {"drivers": drivers, "query": query},
    )


def driver_create(request):
    if request.method == "POST":
        form = DriverForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Driver added successfully.")
            return redirect("fleet:driver_list")
    else:
        form = DriverForm()

    return render(
        request,
        "fleet/driver_form.html",
        {"form": form, "page_title": "Add Driver"},
    )


def driver_update(request, pk):
    driver = get_object_or_404(Driver, pk=pk)

    if request.method == "POST":
        form = DriverForm(request.POST, instance=driver)

        if form.is_valid():
            form.save()
            messages.success(request, "Driver updated successfully.")
            return redirect("fleet:driver_list")
    else:
        form = DriverForm(instance=driver)

    return render(
        request,
        "fleet/driver_form.html",
        {
            "form": form,
            "driver": driver,
            "page_title": "Edit Driver",
        },
    )


def driver_delete(request, pk):
    driver = get_object_or_404(Driver, pk=pk)

    if request.method == "POST":
        try:
            driver.delete()
            messages.success(request, "Driver deleted successfully.")
        except ProtectedError:
            messages.error(
                request,
                "This driver has associated bookings and cannot be deleted.",
            )

        return redirect("fleet:driver_list")

    return render(
        request,
        "fleet/driver_confirm_delete.html",
        {"driver": driver},
    )

def maintenance_list(request):
    maintenance_records = Maintenance.objects.select_related("vehicle").all()

    query = request.GET.get("q", "").strip()
    if query:
        maintenance_records = maintenance_records.filter(
            vehicle__registration_number__icontains=query
        ) | maintenance_records.filter(
            vehicle__make__icontains=query
        ) | maintenance_records.filter(
            vehicle__model__icontains=query
        ) | maintenance_records.filter(
            description__icontains=query
        )

    return render(
        request,
        "fleet/maintenance_list.html",
        {
            "maintenance_records": maintenance_records,
            "query": query,
        },
    )


def maintenance_create(request):
    if request.method == "POST":
        form = MaintenanceForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Maintenance record created successfully.",
            )
            return redirect("fleet:maintenance_list")
    else:
        form = MaintenanceForm()

    return render(
        request,
        "fleet/maintenance_form.html",
        {
            "form": form,
            "page_title": "Schedule Maintenance",
        },
    )


def maintenance_update(request, pk):
    maintenance = get_object_or_404(Maintenance, pk=pk)

    if request.method == "POST":
        form = MaintenanceForm(request.POST, instance=maintenance)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Maintenance record updated successfully.",
            )
            return redirect("fleet:maintenance_list")
    else:
        form = MaintenanceForm(instance=maintenance)

    return render(
        request,
        "fleet/maintenance_form.html",
        {
            "form": form,
            "maintenance": maintenance,
            "page_title": "Edit Maintenance",
        },
    )


def maintenance_delete(request, pk):
    maintenance = get_object_or_404(Maintenance, pk=pk)

    if request.method == "POST":
        try:
            maintenance.delete()
            messages.success(
                request,
                "Maintenance record deleted successfully.",
            )
        except ProtectedError:
            messages.error(
                request,
                "This maintenance record cannot be deleted because it is referenced by another record.",
            )

        return redirect("fleet:maintenance_list")

    return render(
        request,
        "fleet/maintenance_confirm_delete.html",
        {"maintenance": maintenance},
    )
