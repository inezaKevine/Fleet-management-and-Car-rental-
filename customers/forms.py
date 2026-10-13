
from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "customer_type",
            "identification_number",
            "address",
        ]

        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "First name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Last name",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "customer@example.com",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+250...",
            }),
            "customer_type": forms.Select(attrs={
                "class": "form-select",
            }),
            "identification_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "National ID or company identification",
            }),
            "address": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Customer address",
            }),
        }
