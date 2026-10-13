
from django import forms

from .models import Booking, RentalAgreement, Payment, VehicleReturn


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            "customer",
            "vehicle",
            "chauffeur_required",
            "driver",
            "start_at",
            "end_at",
            "special_requests",
        ]
        widgets = {
            "start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "end_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "special_requests": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }


class RentalAgreementForm(forms.ModelForm):
    class Meta:
        model = RentalAgreement
        fields = [
            "booking",
            "agreement_number",
            "terms",
            "signed_at",
        ]
        widgets = {
            "terms": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
            "signed_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            "booking",
            "amount",
            "method",
            "status",
            "transaction_reference",
            "payment_date",
        ]
        labels = {
            "amount": "Amount (RWF)",
            "method": "Payment Method",
            "status": "Payment Status",
            "transaction_reference": "Transaction Reference",
            "payment_date": "Payment Date",
        }
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Enter amount in RWF",
                }
            ),
            "transaction_reference": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "payment_date": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
        }


class VehicleReturnForm(forms.ModelForm):
    class Meta:
        model = VehicleReturn
        fields = [
            "booking",
            "returned_at",
            "mileage",
            "fuel_level",
            "condition_notes",
            "damage_reported",
            "additional_charges",
        ]
        labels = {
            "booking": "Rental Booking",
            "returned_at": "Return Date and Time",
            "mileage": "Odometer Reading (km)",
            "fuel_level": "Fuel Level",
            "condition_notes": "Vehicle Condition Notes",
            "damage_reported": "Was Damage Reported?",
            "additional_charges": "Additional Charges (RWF)",
        }
        widgets = {
            "returned_at": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                }
            ),
            "mileage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1",
                    "placeholder": "Enter odometer reading",
                }
            ),
            "fuel_level": forms.Select(
                choices=[
                    ("", "Select fuel level"),
                    ("Empty", "Empty"),
                    ("1/4", "1/4 tank"),
                    ("1/2", "1/2 tank"),
                    ("3/4", "3/4 tank"),
                    ("Full", "Full tank"),
                ],
                attrs={"class": "form-select"},
            ),
            "condition_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Describe the vehicle's condition "
                        "at the time of return"
                    ),
                }
            ),
            "damage_reported": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "additional_charges": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "Enter additional charges in RWF",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["booking"].queryset = (
            Booking.objects.select_related(
                "customer",
                "vehicle",
            )
            .filter(status__in=["confirmed", "active"])
            .order_by("-created_at")
        )

        self.fields["booking"].widget.attrs.update({
            "class": "form-select",
        })

    def clean_booking(self):
        booking = self.cleaned_data["booking"]

        if hasattr(booking, "vehicle_return"):
            raise forms.ValidationError(
                "A return record already exists for this booking."
            )

        return booking

    def clean(self):
        cleaned_data = super().clean()
        damage_reported = cleaned_data.get("damage_reported")
        condition_notes = cleaned_data.get("condition_notes")

        if damage_reported and not condition_notes:
            self.add_error(
                "condition_notes",
                "Please describe the reported damage.",
            )

        return cleaned_data
