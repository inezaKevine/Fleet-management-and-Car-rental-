
from django.db import models


class Customer(models.Model):
    CUSTOMER_TYPE_CHOICES = [
        ("individual", "Individual"),
        ("company", "Company"),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)

    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        default="individual",
    )

    identification_number = models.CharField(
        max_length=50,
        blank=True,
    )
    address = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
