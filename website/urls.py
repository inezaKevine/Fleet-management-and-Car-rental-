from django.urls import path

from . import views

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("vehicles/", views.vehicle_list, name="vehicle_list"),
    path("book/<int:vehicle_id>/", views.public_booking, name="public_booking"),
    path("booking-success/<int:booking_id>/", views.booking_success, name="booking_success"),
]