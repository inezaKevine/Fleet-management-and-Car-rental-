
from datetime import datetime
from decimal import Decimal
from math import ceil

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from customers.models import Customer
from fleet.models import Vehicle, Maintenance, Driver
from rentals.models import Booking


BLOCKING_STATUSES = ["pending", "confirmed", "active"]


def home(request):
    """Display the public homepage and available vehicles."""
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

    return render(
        request,
        "website/home.html",
        {
            "vehicles": vehicles,
            "search_query": search_query,
        },
    )


def vehicle_list(request):
    """Display and search the public vehicle catalogue."""
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

    return render(
        request,
        "website/vehicle_list.html",
        {
            "vehicles": vehicles,
            "search_query": search_query,
        },
    )


def get_available_drivers(start_at=None, end_at=None):
    """
    Return drivers whose status is available.

    If rental dates are supplied, exclude drivers who already have
    an overlapping pending, confirmed, or active chauffeur booking.
    """
    drivers = Driver.objects.filter(
        status="available"
    )

    if start_at and end_at:
        busy_driver_ids = Booking.objects.filter(
            chauffeur_required=True,
            status__in=BLOCKING_STATUSES,
            start_at__lt=end_at,
            end_at__gt=start_at,
            driver__isnull=False,
        ).values_list("driver_id", flat=True)

        drivers = drivers.exclude(
            pk__in=busy_driver_ids
        )

    return drivers.order_by("id")


def public_booking(request, vehicle_id):
    """Allow a customer to request a vehicle booking from the website."""
    vehicle = get_object_or_404(
        Vehicle,
        pk=vehicle_id,
        status="available",
    )

    form_data = request.POST if request.method == "POST" else {}

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        start_value = request.POST.get("start_at", "").strip()
        end_value = request.POST.get("end_at", "").strip()

        chauffeur_requested = (
            request.POST.get("chauffeur_required") == "on"
        )

        driver_value = request.POST.get("driver", "").strip()
        special_requests = request.POST.get(
            "special_requests", ""
        ).strip()

        errors = []
        start_at = None
        end_at = None
        selected_driver = None

        # ---------------------------------------------------------
        # 1. Validate customer details
        # ---------------------------------------------------------
        if not all([first_name, last_name, email, phone]):
            errors.append(
                "Please complete all your contact details."
            )

        # ---------------------------------------------------------
        # 2. Validate rental dates
        # ---------------------------------------------------------
        try:
            start_at = datetime.fromisoformat(start_value)
            end_at = datetime.fromisoformat(end_value)

            if timezone.is_naive(start_at):
                start_at = timezone.make_aware(
                    start_at,
                    timezone.get_current_timezone(),
                )

            if timezone.is_naive(end_at):
                end_at = timezone.make_aware(
                    end_at,
                    timezone.get_current_timezone(),
                )

            if start_at <= timezone.now():
                errors.append(
                    "The pickup date and time must be in the future."
                )

            if end_at <= start_at:
                errors.append(
                    "The return date and time must be after pickup."
                )

        except (ValueError, TypeError, OverflowError):
            start_at = None
            end_at = None
            errors.append(
                "Please provide valid pickup and return dates."
            )

        # ---------------------------------------------------------
        # 3. Find and validate the selected chauffeur
        # ---------------------------------------------------------
        if chauffeur_requested:
            if not driver_value:
                errors.append(
                    "Please select a driver because you requested "
                    "a chauffeur."
                )
            else:
                try:
                    driver_id = int(driver_value)

                    selected_driver = Driver.objects.filter(
                        pk=driver_id,
                        status="available",
                    ).first()

                    if selected_driver is None:
                        errors.append(
                            "The selected driver is no longer available. "
                            "Please select another driver."
                        )

                except (ValueError, TypeError):
                    errors.append(
                        "Please select a valid driver."
                    )
        else:
            selected_driver = None

        # ---------------------------------------------------------
        # 4. Validate customer email and phone uniqueness
        # ---------------------------------------------------------
        customer = None

        if email and phone:
            customer_by_email = Customer.objects.filter(
                email__iexact=email
            ).first()

            customer_by_phone = Customer.objects.filter(
                phone=phone
            ).first()

            if (
                customer_by_email
                and customer_by_phone
                and customer_by_email.pk != customer_by_phone.pk
            ):
                errors.append(
                    "The email and phone number belong to different "
                    "customer records. Please contact us for assistance."
                )

            elif customer_by_email or customer_by_phone:
                customer = customer_by_email or customer_by_phone

                if customer.email.lower() != email:
                    errors.append(
                        "This phone number is registered with another "
                        "email address. Please contact us for assistance."
                    )

                if customer.phone != phone:
                    errors.append(
                        "This email address is registered with another "
                        "phone number. Please contact us for assistance."
                    )

        # ---------------------------------------------------------
        # 5. Validate vehicle, maintenance, and driver availability
        # ---------------------------------------------------------
        if not errors and start_at and end_at:
            # Refresh the vehicle from the database.
            vehicle = get_object_or_404(
                Vehicle,
                pk=vehicle_id,
                status="available",
            )

            vehicle_conflict = Booking.objects.filter(
                vehicle=vehicle,
                status__in=BLOCKING_STATUSES,
                start_at__lt=end_at,
                end_at__gt=start_at,
            ).exists()

            if vehicle_conflict:
                errors.append(
                    "This vehicle already has a booking during "
                    "your selected dates. Please choose other dates."
                )

            maintenance_conflict = Maintenance.objects.filter(
                vehicle=vehicle,
                status__in=["scheduled", "in_progress"],
                start_date__lt=end_at,
                end_date__gt=start_at,
            ).exists()

            if maintenance_conflict:
                errors.append(
                    "This vehicle is scheduled for maintenance "
                    "during your selected dates."
                )

            if chauffeur_requested and selected_driver:
                driver_conflict = Booking.objects.filter(
                    driver=selected_driver,
                    chauffeur_required=True,
                    status__in=BLOCKING_STATUSES,
                    start_at__lt=end_at,
                    end_at__gt=start_at,
                ).exists()

                if driver_conflict:
                    errors.append(
                        "The selected driver already has a booking "
                        "during these dates. Please choose another driver."
                    )

        # ---------------------------------------------------------
        # 6. Save the customer and booking
        # ---------------------------------------------------------
        if not errors:
            try:
                with transaction.atomic():
                    # Recheck availability inside the transaction
                    # before saving the request.
                    vehicle_conflict = Booking.objects.filter(
                        vehicle=vehicle,
                        status__in=BLOCKING_STATUSES,
                        start_at__lt=end_at,
                        end_at__gt=start_at,
                    ).exists()

                    maintenance_conflict = Maintenance.objects.filter(
                        vehicle=vehicle,
                        status__in=["scheduled", "in_progress"],
                        start_date__lt=end_at,
                        end_date__gt=start_at,
                    ).exists()

                    if vehicle_conflict:
                        errors.append(
                            "This vehicle has just been booked for "
                            "part of your selected period. Please choose "
                            "different dates."
                        )

                    if maintenance_conflict:
                        errors.append(
                            "This vehicle is scheduled for maintenance "
                            "during your selected dates."
                        )

                    if chauffeur_requested and selected_driver:
                        driver_conflict = Booking.objects.filter(
                            driver=selected_driver,
                            chauffeur_required=True,
                            status__in=BLOCKING_STATUSES,
                            start_at__lt=end_at,
                            end_at__gt=start_at,
                        ).exists()

                        driver_status = Driver.objects.filter(
                            pk=selected_driver.pk,
                            status="available",
                        ).exists()

                        if not driver_status or driver_conflict:
                            errors.append(
                                "The selected driver is no longer "
                                "available for these dates. Please "
                                "choose another driver."
                            )

                    if errors:
                        raise ValidationError(errors)

                    if customer is None:
                        customer = Customer(
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            phone=phone,
                            customer_type="individual",
                        )

                        customer.full_clean()
                        customer.save()

                    else:
                        customer.first_name = first_name
                        customer.last_name = last_name
                        customer.full_clean()
                        customer.save(
                            update_fields=[
                                "first_name",
                                "last_name",
                                "updated_at",
                            ]
                        )

                    booking = Booking(
                        customer=customer,
                        vehicle=vehicle,
                        chauffeur_required=chauffeur_requested,
                        driver=selected_driver,
                        start_at=start_at,
                        end_at=end_at,
                        daily_rate=vehicle.daily_rate,
                        status="pending",
                        special_requests=special_requests,
                    )

                    # Use the existing model validation, just like
                    # the internal booking workflow.
                    booking.full_clean()
                    booking.save()

                messages.success(
                    request,
                    "Your booking request has been submitted. "
                    "Our team will review it and contact you.",
                )

                return redirect(
                    "website:booking_success",
                    booking_id=booking.pk,
                )

            except IntegrityError:
                errors.append(
                    "We could not save your request because your "
                    "contact details may already exist. Please check "
                    "your email and phone number."
                )

            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field_errors in exc.message_dict.values():
                        errors.extend(field_errors)
                else:
                    errors.extend(exc.messages)

        for error in errors:
            messages.error(request, error)

        available_drivers = get_available_drivers(
            start_at=start_at,
            end_at=end_at,
        )

        # If the customer selected a driver that is now unavailable,
        # do not leave that driver in the list as an available option.
        if selected_driver and not available_drivers.filter(
            pk=selected_driver.pk
        ).exists():
            selected_driver = None

        return render(
            request,
            "website/public_booking.html",
            {
                "vehicle": vehicle,
                "form_data": form_data,
                "available_drivers": available_drivers,
            },
        )

    # Initial page load: show currently available drivers.
    return render(
        request,
        "website/public_booking.html",
        {
            "vehicle": vehicle,
            "form_data": {},
            "available_drivers": get_available_drivers(),
        },
    )


def booking_success(request, booking_id):
    """Display the confirmation page for a pending booking request."""
    booking = get_object_or_404(
        Booking.objects.select_related(
            "vehicle",
            "customer",
            "driver",
        ),
        pk=booking_id,
        status="pending",
    )

    duration_seconds = (
        booking.end_at - booking.start_at
    ).total_seconds()

    rental_days = max(1, ceil(duration_seconds / 86400))

    estimated_total = (
        booking.daily_rate * rental_days
    ).quantize(Decimal("0.01"))

    return render(
        request,
        "website/booking_success.html",
        {
            "booking": booking,
            "rental_days": rental_days,
            "estimated_total": estimated_total,
        },
    )
