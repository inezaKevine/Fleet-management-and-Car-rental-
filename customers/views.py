
from django.shortcuts import render
from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404

from .models import Customer
from .forms import CustomerForm


def customer_list(request):
    customers = Customer.objects.all()

    query = request.GET.get("q", "").strip()
    if query:
        customers = customers.filter(
            first_name__icontains=query
        ) | customers.filter(
            last_name__icontains=query
        ) | customers.filter(
            email__icontains=query
        ) | customers.filter(
            phone__icontains=query
        )

    return render(
        request,
        "customers/customer_list.html",
        {
            "customers": customers,
            "query": query,
        },
    )


def customer_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Customer registered successfully.",
            )
            return redirect("customers:customer_list")
    else:
        form = CustomerForm()

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "page_title": "Register Customer",
        },
    )


def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Customer details updated successfully.",
            )
            return redirect("customers:customer_list")
    else:
        form = CustomerForm(instance=customer)

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "customer": customer,
            "page_title": "Edit Customer",
        },
    )


def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        try:
            customer.delete()
            messages.success(
                request,
                "Customer deleted successfully.",
            )
        except ProtectedError:
            messages.error(
                request,
                "This customer has associated bookings and cannot be deleted.",
            )

        return redirect("customers:customer_list")

    return render(
        request,
        "customers/customer_confirm_delete.html",
        {"customer": customer},
    )

