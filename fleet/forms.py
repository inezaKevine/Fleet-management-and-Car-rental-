
from django import forms
from .models import Vehicle
from .models import Driver
from .models import Maintenance

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "registration_number",
            "make",
            "model",
            "year",
            "color",
            "description",
            "daily_rate",
            "image",
            "status",
        ]

        widgets = {
            "registration_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. RAB 123 A",
            }),
            "make": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Toyota",
            }),
            "model": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. RAV4",
            }),
            "year": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1900",
            }),
            "color": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Vehicle color",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Additional vehicle details",
            }),
            "daily_rate": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": "Daily rental price",
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
            "status": forms.Select(attrs={
                "class": "form-select",
            }),
        }

    def clean_registration_number(self):
        return self.cleaned_data["registration_number"].strip().upper()




class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            "first_name",
            "last_name",
            "phone",
            "email",
            "licence_number",
            "licence_expiry",
            "status",
        ]

        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter first name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter last name",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. +250788123456",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "driver@example.com",
            }),
            "licence_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Driving licence number",
            }),
            "licence_expiry": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "status": forms.Select(attrs={
                "class": "form-select",
            }),
        }
class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = [
            "vehicle",
            "description",
            "start_date",
            "end_date",
            "cost",
            "status",
        ]

        widgets = {
            "vehicle": forms.Select(attrs={
                "class": "form-select",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe the maintenance work",
            }),
            "start_date": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }, format="%Y-%m-%dT%H:%M"),
            "end_date": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }, format="%Y-%m-%dT%H:%M"),
            "cost": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": "Enter cost in RWF",
            }),
            "status": forms.Select(attrs={
                "class": "form-select",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["start_date"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]
        self.fields["end_date"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]