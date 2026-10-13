
from django.urls import path
from . import views

app_name = "fleet"

urlpatterns = [
    path("", views.vehicle_list, name="vehicle_list"),
    path("add/", views.vehicle_create, name="vehicle_create"),
    path("<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("<int:pk>/edit/", views.vehicle_update, name="vehicle_update"),
    path("<int:pk>/delete/", views.vehicle_delete, name="vehicle_delete"),

    
path("drivers/", views.driver_list, name="driver_list"),
path("drivers/add/", views.driver_create, name="driver_create"),
path("drivers/<int:pk>/edit/", views.driver_update, name="driver_update"),
path("drivers/<int:pk>/delete/", views.driver_delete, name="driver_delete"),


path("maintenance/", views.maintenance_list, name="maintenance_list"),
path("maintenance/add/", views.maintenance_create, name="maintenance_create"),
path("maintenance/<int:pk>/edit/", views.maintenance_update, name="maintenance_update"),
path("maintenance/<int:pk>/delete/", views.maintenance_delete, name="maintenance_delete"),
]
