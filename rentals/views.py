
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from fleet.models import Driver, Maintenance

from .forms import (
    BookingForm,
    PaymentForm,
    RentalAgreementForm,
    VehicleReturnForm,
)
from .models import Booking, Payment, RentalAgreement, VehicleReturn


BLOCKING_STATUSES = ["pending", "confirmed", "active"]


def get_booking_conflicts(booking):
    """Return maintenance and booking conflicts for a booking."""
    conflicts = []

    maintenance_conflicts = Maintenance.objects.filter(
        vehicle_id=booking.vehicle_id,
        status__in=["scheduled", "in_progress"],
        start_date__lt=booking.end_at,
        end_date__gt=booking.start_at,
    )

    for record in maintenance_conflicts:
        conflicts.append(
            f"Maintenance: {record.description} "
            f"({record.start_date:%d %b %Y %H:%M} - "
            f"{record.end_date:%d %b %Y %H:%M})"
        )

    other_bookings = Booking.objects.filter(
        status__in=BLOCKING_STATUSES,
        start_at__lt=booking.end_at,
        end_at__gt=booking.start_at,
    ).exclude(pk=booking.pk)

    if other_bookings.filter(vehicle_id=booking.vehicle_id).exists():
        conflicts.append("Vehicle has another booking during this period.")

    if booking.driver_id and booking.chauffeur_required:
        driver_conflicts = other_bookings.filter(
            driver_id=booking.driver_id,
            chauffeur_required=True,
        )

        if driver_conflicts.exists():
            conflicts.append(
                "Assigned driver has another booking during this period."
            )

    return conflicts


def booking_list(request):
    bookings = Booking.objects.select_related(
        "customer", "vehicle", "driver"
    ).all()

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if query:
        bookings = bookings.filter(
            Q(customer__first_name__icontains=query)
            | Q(customer__last_name__icontains=query)
            | Q(customer__email__icontains=query)
            | Q(customer__phone__icontains=query)
            | Q(vehicle__registration_number__icontains=query)
            | Q(vehicle__make__icontains=query)
            | Q(vehicle__model__icontains=query)
        )

    valid_statuses = dict(Booking.STATUS_CHOICES)

    if status in valid_statuses:
        bookings = bookings.filter(status=status)
    else:
        status = ""

    for booking in bookings:
        booking.availability_conflicts = get_booking_conflicts(booking)
        booking.has_availability_conflict = bool(
            booking.availability_conflicts
        )

    return render(
        request,
        "rentals/booking_list.html",
        {
            "bookings": bookings,
            "query": query,
            "selected_status": status,
            "status_choices": Booking.STATUS_CHOICES,
        },
    )


def booking_create(request):
    if request.method == "POST":
        form = BookingForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    booking = form.save(commit=False)
                    booking.status = "pending"
                    booking.daily_rate = booking.vehicle.daily_rate
                    booking.full_clean()
                    booking.save()

                messages.success(
                    request,
                    "Booking request created successfully. "
                    "It is awaiting staff approval.",
                )
                return redirect("rentals:booking_list")

            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, errors in exc.message_dict.items():
                        if field in form.fields:
                            for error in errors:
                                form.add_error(field, error)
                        else:
                            for error in errors:
                                form.add_error(None, error)
                else:
                    for error in exc.messages:
                        form.add_error(None, error)
    else:
        form = BookingForm()

    return render(
        request,
        "rentals/booking_form.html",
        {
            "form": form,
            "page_title": "Create Booking Request",
        },
    )


def booking_approve(request, pk):
    if request.method != "POST":
        return redirect("rentals:booking_list")

    try:
        with transaction.atomic():
            booking = get_object_or_404(
                Booking.objects.select_for_update(),
                pk=pk,
            )

            if booking.status != "pending":
                messages.warning(
                    request,
                    "Only pending bookings can be approved.",
                )
                return redirect("rentals:booking_list")

            booking.daily_rate = booking.vehicle.daily_rate
            booking.status = "confirmed"
            booking.full_clean()
            booking.save()

        messages.success(
            request,
            f"Booking #{booking.pk} has been approved successfully.",
        )

    except ValidationError as exc:
        messages.error(
            request,
            "Booking could not be approved: " + " ".join(exc.messages),
        )

    return redirect("rentals:booking_list")


def booking_reject(request, pk):
    if request.method != "POST":
        return redirect("rentals:booking_list")

    booking = get_object_or_404(Booking, pk=pk)

    if booking.status != "pending":
        messages.warning(
            request,
            "Only pending bookings can be rejected.",
        )
        return redirect("rentals:booking_list")

    booking.status = "cancelled"
    booking.save(update_fields=["status"])

    messages.success(
        request,
        f"Booking #{booking.pk} has been rejected.",
    )
    return redirect("rentals:booking_list")


def booking_availability_check(request):
    if request.method != "GET":
        return JsonResponse(
            {"error": "GET requests only."},
            status=405,
        )

    vehicle_id = request.GET.get("vehicle")
    driver_id = request.GET.get("driver")
    start_value = request.GET.get("start_at")
    end_value = request.GET.get("end_at")
    chauffeur_required = (
        request.GET.get("chauffeur_required") == "true"
    )

    if not all([vehicle_id, start_value, end_value]):
        return JsonResponse({
            "checked": False,
            "conflicts": [],
            "message": (
                "Select a vehicle and both rental dates "
                "to check availability."
            ),
        })

    try:
        start_at = datetime.fromisoformat(start_value)
        end_at = datetime.fromisoformat(end_value)

        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(
                start_at, timezone.get_current_timezone()
            )

        if timezone.is_naive(end_at):
            end_at = timezone.make_aware(
                end_at, timezone.get_current_timezone()
            )

        if end_at <= start_at:
            return JsonResponse({
                "checked": False,
                "conflicts": [],
                "message": "The return date must be after pickup.",
            })

        vehicle_id = int(vehicle_id)

    except (ValueError, TypeError):
        return JsonResponse({
            "checked": False,
            "conflicts": [],
            "message": "Please enter valid rental details.",
        })

    conflicts = []

    vehicle_bookings = Booking.objects.filter(
        vehicle_id=vehicle_id,
        status__in=BLOCKING_STATUSES,
        start_at__lt=end_at,
        end_at__gt=start_at,
    )

    if vehicle_bookings.exists():
        conflicts.append(
            "This vehicle has another booking during the selected period."
        )

    maintenance_records = Maintenance.objects.filter(
        vehicle_id=vehicle_id,
        status__in=["scheduled", "in_progress"],
        start_date__lt=end_at,
        end_date__gt=start_at,
    )

    for record in maintenance_records:
        conflicts.append(
            f"Maintenance conflict: {record.description} "
            f"({record.start_date:%d %b %Y %H:%M} - "
            f"{record.end_date:%d %b %Y %H:%M})."
        )

    if chauffeur_required:
        if not driver_id:
            conflicts.append(
                "Select a driver because a chauffeur is required."
            )
        else:
            try:
                driver_id = int(driver_id)
                driver = Driver.objects.filter(pk=driver_id).first()

                if not driver or driver.status != "available":
                    conflicts.append("The selected driver is not available.")
                else:
                    driver_bookings = Booking.objects.filter(
                        driver_id=driver_id,
                        chauffeur_required=True,
                        status__in=BLOCKING_STATUSES,
                        start_at__lt=end_at,
                        end_at__gt=start_at,
                    )

                    if driver_bookings.exists():
                        conflicts.append(
                            "The selected driver has another booking "
                            "during this period."
                        )

            except (ValueError, TypeError):
                conflicts.append("Please select a valid driver.")

    return JsonResponse({
        "checked": True,
        "available": not conflicts,
        "conflicts": conflicts,
        "message": (
            "No scheduling conflicts found."
            if not conflicts
            else "Please resolve the conflicts before submitting."
        ),
    })


def agreement_list(request):
    agreements = RentalAgreement.objects.select_related(
        "booking",
        "booking__customer",
        "booking__vehicle",
    ).order_by("-created_at")

    return render(
        request,
        "rentals/agreement_list.html",
        {"agreements": agreements},
    )


def agreement_create(request):
    if request.method == "POST":
        form = RentalAgreementForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    agreement = form.save(commit=False)
                    agreement.full_clean()
                    agreement.save()

                messages.success(
                    request,
                    f"Rental agreement {agreement.agreement_number} "
                    "was created successfully.",
                )
                return redirect("rentals:agreement_list")

            except IntegrityError:
                form.add_error(
                    "booking",
                    "An agreement already exists for this booking.",
                )

            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, errors in exc.message_dict.items():
                        if field in form.fields:
                            for error in errors:
                                form.add_error(field, error)
                        else:
                            for error in errors:
                                form.add_error(None, error)
                else:
                    for error in exc.messages:
                        form.add_error(None, error)
    else:
        form = RentalAgreementForm()

    return render(
        request,
        "rentals/agreement_form.html",
        {
            "form": form,
            "page_title": "Create Rental Agreement",
        },
    )


def get_booking_payment_summary(booking):
    """Calculate the rental charge, amount paid, and remaining balance."""
    duration_seconds = (
        booking.end_at - booking.start_at
    ).total_seconds()

    rental_days = max(1, ceil(duration_seconds / 86400))

    rental_total = (
        booking.daily_rate * rental_days
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    paid_total = (
        booking.payments.filter(status="paid")
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    paid_total = paid_total.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    outstanding = max(
        Decimal("0.00"),
        rental_total - paid_total,
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    return {
        "rental_days": rental_days,
        "rental_total": rental_total,
        "paid_total": paid_total,
        "outstanding": outstanding,
    }


def payment_list(request):
    payments = Payment.objects.select_related(
        "booking",
        "booking__customer",
        "booking__vehicle",
    ).order_by("-created_at")

    booking_summaries = {}

    for payment in payments:
        booking_id = payment.booking_id

        if booking_id not in booking_summaries:
            summary = get_booking_payment_summary(payment.booking)

            if summary["outstanding"] <= 0:
                payment_status = "Fully Paid"
            elif summary["paid_total"] > 0:
                payment_status = "Partially Paid"
            else:
                payment_status = "Unpaid"

            booking_summaries[booking_id] = {
                **summary,
                "payment_status": payment_status,
            }

        payment.booking_summary = booking_summaries[booking_id]

    return render(
        request,
        "rentals/payment_list.html",
        {"payments": payments},
    )


def payment_create(request):
    if request.method == "POST":
        form = PaymentForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)

                    booking = Booking.objects.select_for_update().get(
                        pk=payment.booking_id
                    )
                    payment.booking = booking

                    summary = get_booking_payment_summary(booking)
                    amount = payment.amount

                    if summary["outstanding"] <= 0:
                        form.add_error(
                            "booking",
                            "This booking has no outstanding balance.",
                        )
                    elif amount <= Decimal("0.00"):
                        form.add_error(
                            "amount",
                            "The payment amount must be greater than zero.",
                        )
                    elif amount > summary["outstanding"]:
                        form.add_error(
                            "amount",
                            "The amount cannot exceed the outstanding "
                            f"balance of RWF {summary['outstanding']:,.2f}.",
                        )
                    else:
                        if (
                            payment.status == "paid"
                            and not payment.payment_date
                        ):
                            payment.payment_date = timezone.now()

                        payment.full_clean()
                        payment.save()

                        messages.success(
                            request,
                            "Payment recorded successfully.",
                        )
                        return redirect("rentals:payment_list")

            except Booking.DoesNotExist:
                form.add_error(
                    "booking",
                    "The selected booking could not be found.",
                )

            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, errors in exc.message_dict.items():
                        if field in form.fields:
                            for error in errors:
                                form.add_error(field, error)
                        else:
                            for error in errors:
                                form.add_error(None, error)
                else:
                    for error in exc.messages:
                        form.add_error(None, error)
    else:
        form = PaymentForm()

    return render(
        request,
        "rentals/payment_form.html",
        {
            "form": form,
            "page_title": "Record Payment",
        },
    )


def payment_booking_summary(request):
    if request.method != "GET":
        return JsonResponse(
            {"error": "GET requests only."},
            status=405,
        )

    booking_id = request.GET.get("booking")

    if not booking_id:
        return JsonResponse({
            "selected": False,
            "message": "Select a booking to calculate the balance.",
        })

    try:
        booking = Booking.objects.select_related(
            "customer",
            "vehicle",
        ).get(pk=int(booking_id))
    except (Booking.DoesNotExist, ValueError, TypeError):
        return JsonResponse(
            {"error": "Invalid booking."},
            status=400,
        )

    summary = get_booking_payment_summary(booking)

    return JsonResponse({
        "selected": True,
        "booking": str(booking),
        "rental_days": summary["rental_days"],
        "rental_total": str(summary["rental_total"]),
        "paid_total": str(summary["paid_total"]),
        "outstanding": str(summary["outstanding"]),
    })


def payment_delete(request, pk):
    """Local testing helper; replace with an audited process for production."""
    if request.method != "POST":
        return redirect("rentals:payment_list")

    payment = get_object_or_404(Payment, pk=pk)
    payment_id = payment.pk
    payment.delete()

    messages.success(
        request,
        f"Test payment #{payment_id} deleted successfully.",
    )
    return redirect("rentals:payment_list")


def vehicle_return_list(request):
    returns = VehicleReturn.objects.select_related(
        "booking",
        "booking__customer",
        "booking__vehicle",
    ).order_by("-returned_at")

    query = request.GET.get("q", "").strip()

    if query:
        returns = returns.filter(
            Q(booking__customer__first_name__icontains=query)
            | Q(booking__customer__last_name__icontains=query)
            | Q(booking__vehicle__registration_number__icontains=query)
            | Q(booking__vehicle__make__icontains=query)
            | Q(booking__vehicle__model__icontains=query)
        )

    return render(
        request,
        "rentals/vehicle_return_list.html",
        {
            "returns": returns,
            "query": query,
        },
    )


def vehicle_return_create(request):
    if request.method == "POST":
        form = VehicleReturnForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    booking = Booking.objects.select_for_update().get(
                        pk=form.cleaned_data["booking"].pk
                    )

                    if booking.status not in ["confirmed", "active"]:
                        form.add_error(
                            "booking",
                            "Only confirmed or active bookings can be returned.",
                        )
                    elif VehicleReturn.objects.filter(
                        booking=booking
                    ).exists():
                        form.add_error(
                            "booking",
                            "A return record already exists for this booking.",
                        )
                    else:
                        vehicle_return = form.save(commit=False)
                        vehicle_return.booking = booking
                        vehicle_return.full_clean()
                        vehicle_return.save()

                        # Complete the booking only after the return is recorded.
                        booking.status = "completed"
                        booking.save(update_fields=["status"])

                        messages.success(
                            request,
                            "Vehicle return recorded successfully. "
                            "Review the vehicle condition before making "
                            "the vehicle available for another rental.",
                        )
                        return redirect("rentals:vehicle_return_list")

            except Booking.DoesNotExist:
                form.add_error(
                    "booking",
                    "The selected booking could not be found.",
                )

            except IntegrityError:
                form.add_error(
                    "booking",
                    "A return record already exists for this booking.",
                )

            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, errors in exc.message_dict.items():
                        if field in form.fields:
                            for error in errors:
                                form.add_error(field, error)
                        else:
                            for error in errors:
                                form.add_error(None, error)
                else:
                    for error in exc.messages:
                        form.add_error(None, error)
    else:
        form = VehicleReturnForm()

    return render(
        request,
        "rentals/vehicle_return_form.html",
        {
            "form": form,
            "page_title": "Record Vehicle Return",
        },
    )
