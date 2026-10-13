
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone

from fleet.models import Vehicle, Driver
from customers.models import Customer


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    chauffeur_required = models.BooleanField(default=False)

    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="bookings",
        null=True,
        blank=True,
    )

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        errors = {}

        if self.start_at and self.end_at:
            if self.end_at <= self.start_at:
                errors["end_at"] = (
                    "The end time must be after the start time."
                )

        if self.chauffeur_required and not self.driver_id:
            errors["driver"] = (
                "Please assign a driver for a chauffeur booking."
            )

        if not self.chauffeur_required and self.driver_id:
            errors["driver"] = (
                "A driver can only be assigned when a chauffeur is requested."
            )

        blocking_statuses = ["pending", "confirmed", "active"]

        valid_period = (
            self.start_at
            and self.end_at
            and self.end_at > self.start_at
        )

        if valid_period and self.status in blocking_statuses:
            if self.vehicle_id:
                conflicts = Booking.objects.filter(
                    vehicle_id=self.vehicle_id,
                    status__in=blocking_statuses,
                    start_at__lt=self.end_at,
                    end_at__gt=self.start_at,
                )

                if self.pk:
                    conflicts = conflicts.exclude(pk=self.pk)

                if conflicts.exists():
                    errors["vehicle"] = (
                        "This vehicle is already booked during "
                        "the selected period."
                    )

                maintenance_conflicts = (
                    self.vehicle.maintenance_records.filter(
                        status__in=["scheduled", "in_progress"],
                        start_date__lt=self.end_at,
                        end_date__gt=self.start_at,
                    )
                )

                if maintenance_conflicts.exists():
                    errors["vehicle"] = (
                        "This vehicle is scheduled for maintenance "
                        "during the selected period."
                    )

            if self.driver_id and self.chauffeur_required:
                driver_conflicts = Booking.objects.filter(
                    driver_id=self.driver_id,
                    chauffeur_required=True,
                    status__in=blocking_statuses,
                    start_at__lt=self.end_at,
                    end_at__gt=self.start_at,
                )

                if self.pk:
                    driver_conflicts = driver_conflicts.exclude(
                        pk=self.pk
                    )

                if driver_conflicts.exists():
                    errors["driver"] = (
                        "This driver is already assigned to another "
                        "booking during that period."
                    )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Booking #{self.pk or 'New'} - {self.vehicle}"


class RentalAgreement(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="agreement",
    )

    agreement_number = models.CharField(
        max_length=50,
        unique=True,
    )

    terms = models.TextField()
    signed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.agreement_number


class Payment(models.Model):
    METHOD_CHOICES = [
        ("cash", "Cash"),
        ("bank_transfer", "Bank Transfer"),
        ("card", "Card"),
        ("mobile_money", "Mobile Money"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    method = models.CharField(max_length=20, choices=METHOD_CHOICES)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.pk} - {self.amount}"


class VehicleReturn(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="vehicle_return",
    )

    returned_at = models.DateTimeField(default=timezone.now)
    mileage = models.PositiveIntegerField()
    fuel_level = models.CharField(max_length=30, blank=True)
    condition_notes = models.TextField(blank=True)
    damage_reported = models.BooleanField(default=False)

    additional_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    def __str__(self):
        return f"Return for {self.booking}"
