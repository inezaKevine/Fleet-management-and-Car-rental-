from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.db.models.fields import DateField, DateTimeField
from django.utils import timezone
from django.shortcuts import render

from fleet.models import Vehicle, Driver, Maintenance
from customers.models import Customer
from rentals.models import (
    Booking,
    RentalAgreement,
    Payment,
    VehicleReturn,
)


# ---------------------------------------------------------
# MODEL HELPERS
# ---------------------------------------------------------

def get_field(model, candidates, accepted_types=None):
    """Return the first existing model field matching the candidates."""
    for name in candidates:
        try:
            field = model._meta.get_field(name)
        except Exception:
            continue

        if not getattr(field, "concrete", False):
            continue

        if getattr(field, "many_to_many", False):
            continue

        if accepted_types:
            if field.get_internal_type() not in accepted_types:
                continue

        return field

    return None


def get_status_field(model):
    field = get_field(
        model,
        ["status", "booking_status", "payment_status", "state"],
        ["CharField", "TextField"],
    )
    return field.name if field else None


def get_date_field(model, candidates):
    field = get_field(
        model,
        candidates,
        ["DateField", "DateTimeField"],
    )
    return field.name if field else None


def get_amount_field(model):
    field = get_field(
        model,
        [
            "amount",
            "total_amount",
            "payment_amount",
            "paid_amount",
            "total_price",
            "total_cost",
        ],
        ["DecimalField", "FloatField", "IntegerField", "BigIntegerField"],
    )
    return field.name if field else None


def count_status(model, statuses):
    """Count records matching one of the supplied statuses."""
    status_field = get_status_field(model)

    if not status_field:
        return 0

    condition = Q()

    for status in statuses:
        condition |= Q(**{f"{status_field}__iexact": status})

    return model.objects.filter(condition).count()


def status_distribution(model, fallback_labels, fallback_values):
    """Aggregate the actual status values stored in the database."""
    status_field = get_status_field(model)

    if not status_field:
        return fallback_labels, fallback_values

    rows = (
        model.objects
        .values(status_field)
        .annotate(total=Count("pk"))
        .order_by("-total")
    )

    labels = []
    values = []

    for row in rows:
        value = row[status_field]
        label = str(value).replace("_", " ").title() if value else "Unspecified"

        labels.append(label)
        values.append(row["total"])

    if not labels:
        return fallback_labels, fallback_values

    return labels, values


def successful_payments():
    """Identify successfully collected payments where status is available."""
    status_field = get_status_field(Payment)
    queryset = Payment.objects.all()

    if not status_field:
        return queryset

    condition = Q()

    for value in ["paid", "completed", "successful", "success"]:
        condition |= Q(**{f"{status_field}__iexact": value})

    return queryset.filter(condition)


# ---------------------------------------------------------
# MONTHLY ANALYTICS
# ---------------------------------------------------------

def get_last_months(number=6):
    """Return month/year pairs, including the current month."""
    today = timezone.localdate()
    months = []

    year = today.year
    month = today.month

    for _ in range(number):
        months.append((year, month))

        month -= 1
        if month == 0:
            month = 12
            year -= 1

    months.reverse()

    return [
        (year, month, date(year, month, 1).strftime("%b %Y"))
        for year, month in months
    ]


def monthly_counts(model, date_candidates, months):
    """Count actual records for each month."""
    date_field = get_date_field(model, date_candidates)
    results = []

    for year, month, label in months:
        if not date_field:
            results.append(0)
            continue

        filters = {
            f"{date_field}__year": year,
            f"{date_field}__month": month,
        }

        results.append(model.objects.filter(**filters).count())

    return results


def monthly_revenue(months):
    """Calculate paid revenue by month from payment records."""
    date_field = get_date_field(
        Payment,
        [
            "payment_date",
            "paid_at",
            "created_at",
            "created_on",
            "date_created",
            "transaction_date",
            "date",
        ],
    )

    amount_field = get_amount_field(Payment)
    payments = successful_payments()
    results = []

    for year, month, label in months:
        if not date_field or not amount_field:
            results.append(0.0)
            continue

        filters = {
            f"{date_field}__year": year,
            f"{date_field}__month": month,
        }

        total = payments.filter(**filters).aggregate(
            total=Sum(amount_field)
        )["total"]

        results.append(float(total or Decimal("0.00")))

    return results


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

@login_required
def dashboard(request):
    today = timezone.localdate()

    # Fleet statistics
    total_vehicles = Vehicle.objects.count()
    available_vehicles = count_status(Vehicle, ["available"])

    rented_vehicles = count_status(
        Vehicle,
        ["rented", "booked", "in_use", "in use"],
    )

    maintenance_vehicles = count_status(
        Vehicle,
        ["maintenance", "under maintenance", "in_maintenance"],
    )

    total_drivers = Driver.objects.count()
    available_drivers = count_status(Driver, ["available"])

    # Customer and booking statistics
    total_customers = Customer.objects.count()
    total_bookings = Booking.objects.count()

    pending_bookings = count_status(Booking, ["pending"])
    confirmed_bookings = count_status(Booking, ["confirmed"])
    active_bookings = count_status(
        Booking, ["active", "ongoing", "in_progress"]
    )
    completed_bookings = count_status(
        Booking, ["completed", "complete"]
    )
    cancelled_bookings = count_status(
        Booking, ["cancelled", "canceled"]
    )

    # Payments
    total_payments = Payment.objects.count()
    paid_payments = successful_payments()
    paid_payment_count = paid_payments.count()

    amount_field = get_amount_field(Payment)

    if amount_field:
        total_revenue = paid_payments.aggregate(
            total=Sum(amount_field)
        )["total"] or Decimal("0.00")
    else:
        total_revenue = Decimal("0.00")

    pending_payment_count = count_status(Payment, ["pending"])

    # Other modules
    total_agreements = RentalAgreement.objects.count()
    total_returns = VehicleReturn.objects.count()

    # Monthly booking trend: prefer creation date, then booking dates.
    months = get_last_months(6)
    month_labels = [label for year, month, label in months]

    booking_monthly_counts = monthly_counts(
        Booking,
        [
            "created_at",
            "created_on",
            "date_created",
            "booking_date",
            "start_date",
            "pickup_date",
        ],
        months,
    )

    revenue_monthly_values = monthly_revenue(months)

    # Real status distributions
    booking_status_labels, booking_status_values = status_distribution(
        Booking,
        ["Pending", "Confirmed", "Active", "Completed", "Cancelled"],
        [
            pending_bookings,
            confirmed_bookings,
            active_bookings,
            completed_bookings,
            cancelled_bookings,
        ],
    )

    vehicle_status_labels, vehicle_status_values = status_distribution(
        Vehicle,
        ["Available", "Rented", "Maintenance"],
        [
            available_vehicles,
            rented_vehicles,
            maintenance_vehicles,
        ],
    )

    payment_status_labels, payment_status_values = status_distribution(
        Payment,
        ["Paid", "Pending", "Other"],
        [
            paid_payment_count,
            pending_payment_count,
            max(
                total_payments
                - paid_payment_count
                - pending_payment_count,
                0,
            ),
        ],
    )

    # Operational rates
    fleet_utilization = (
        round((rented_vehicles / total_vehicles) * 100, 1)
        if total_vehicles else 0
    )

    fleet_availability = (
        round((available_vehicles / total_vehicles) * 100, 1)
        if total_vehicles else 0
    )

    payment_collection_rate = (
        round((paid_payment_count / total_payments) * 100, 1)
        if total_payments else 0
    )

    completed_booking_rate = (
        round((completed_bookings / total_bookings) * 100, 1)
        if total_bookings else 0
    )

    # Recent bookings, using real model relations when present
    booking_relations = []

    for name in ["customer", "vehicle", "driver"]:
        try:
            field = Booking._meta.get_field(name)
            if field.is_relation and field.many_to_one:
                booking_relations.append(name)
        except Exception:
            pass

    recent_booking_queryset = Booking.objects.all()

    if booking_relations:
        recent_booking_queryset = recent_booking_queryset.select_related(
            *booking_relations
        )

    booking_date_field = get_date_field(
        Booking,
        ["created_at", "created_on", "date_created"],
    )

    if booking_date_field:
        recent_booking_queryset = recent_booking_queryset.order_by(
            f"-{booking_date_field}"
        )
    else:
        recent_booking_queryset = recent_booking_queryset.order_by("-pk")

    recent_bookings = recent_booking_queryset[:7]

    # Maintenance alerts
    maintenance_queryset = Maintenance.objects.all()
    maintenance_status_field = get_status_field(Maintenance)

    if maintenance_status_field:
        maintenance_condition = Q()

        for status in [
            "scheduled",
            "pending",
            "in_progress",
            "ongoing",
        ]:
            maintenance_condition |= Q(
                **{f"{maintenance_status_field}__iexact": status}
            )

        maintenance_queryset = maintenance_queryset.filter(
            maintenance_condition
        )

    maintenance_date_field = get_date_field(
        Maintenance,
        ["start_date", "scheduled_date", "maintenance_date", "created_at"],
    )

    if maintenance_date_field:
        maintenance_queryset = maintenance_queryset.order_by(
            maintenance_date_field
        )

    maintenance_alerts = maintenance_queryset[:5]

    context = {
        "today": today,

        "total_vehicles": total_vehicles,
        "available_vehicles": available_vehicles,
        "rented_vehicles": rented_vehicles,
        "maintenance_vehicles": maintenance_vehicles,

        "total_drivers": total_drivers,
        "available_drivers": available_drivers,
        "total_customers": total_customers,
        "total_bookings": total_bookings,

        "pending_bookings": pending_bookings,
        "confirmed_bookings": confirmed_bookings,
        "active_bookings": active_bookings,
        "completed_bookings": completed_bookings,
        "cancelled_bookings": cancelled_bookings,

        "total_payments": total_payments,
        "paid_payments": paid_payments,
        "paid_payment_count": paid_payment_count,
        "pending_payment_count": pending_payment_count,
        "total_revenue": total_revenue,

        "total_agreements": total_agreements,
        "total_returns": total_returns,

        "recent_bookings": recent_bookings,
        "maintenance_alerts": maintenance_alerts,

        # Chart.js data
        "month_labels": month_labels,
        "booking_monthly_counts": booking_monthly_counts,
        "revenue_monthly_values": revenue_monthly_values,

        "booking_status_labels": booking_status_labels,
        "booking_status_values": booking_status_values,

        "vehicle_status_labels": vehicle_status_labels,
        "vehicle_status_values": vehicle_status_values,

        "payment_status_labels": payment_status_labels,
        "payment_status_values": payment_status_values,

        # Performance metrics
        "fleet_utilization": fleet_utilization,
        "fleet_availability": fleet_availability,
        "payment_collection_rate": payment_collection_rate,
        "completed_booking_rate": completed_booking_rate,
    }

    return render(request, "dashboard/dashboard.html", context)