
from django.urls import path
from . import views

app_name = "rentals"

urlpatterns = [
    # Bookings
    path("", views.booking_list, name="booking_list"),
    path("add/", views.booking_create, name="booking_create"),
    path("<int:pk>/approve/", views.booking_approve, name="booking_approve"),
    path("<int:pk>/reject/", views.booking_reject, name="booking_reject"),
    path(
        "availability-check/",
        views.booking_availability_check,
        name="booking_availability_check",
    ),

    # Rental Agreements
    path("agreements/", views.agreement_list, name="agreement_list"),
    path("agreements/add/", views.agreement_create, name="agreement_create"),

    # Payments
    path("payments/", views.payment_list, name="payment_list"),
    path("payments/add/", views.payment_create, name="payment_create"),
    path(
        "payments/booking-summary/",
        views.payment_booking_summary,
        name="payment_booking_summary",
    ),
    path(
        "payments/<int:pk>/delete/",
        views.payment_delete,
        name="payment_delete",
    ),

    # Vehicle Returns
    path(
        "returns/",
        views.vehicle_return_list,
        name="vehicle_return_list",
    ),
    path(
        "returns/add/",
        views.vehicle_return_create,
        name="vehicle_return_create",
    ),
]
