
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class Vehicle(models.Model):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("rented", "Rented"),
        ("maintenance", "Under Maintenance"),
        ("inactive", "Inactive"),
    ]

    registration_number = models.CharField(
        max_length=20,
        unique=True,
    )
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    color = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)

    daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    image = models.ImageField(
        upload_to="vehicles/",
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["registration_number"]

    def __str__(self):
        return (
            f"{self.registration_number} - "
            f"{self.make} {self.model}"
        )


class Driver(models.Model):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("unavailable", "Unavailable"),
        ("inactive", "Inactive"),
    ]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
    licence_number = models.CharField(
        max_length=50,
        unique=True,
    )
    licence_expiry = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Maintenance(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="maintenance_records",
    )

    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def clean(self):
        if (
            self.start_date
            and self.end_date
            and self.end_date <= self.start_date
        ):
            raise ValidationError({
                "end_date": (
                    "The end date must be after the start date."
                )
            })

    def __str__(self):
        return f"{self.vehicle} - {self.description[:40]}"
