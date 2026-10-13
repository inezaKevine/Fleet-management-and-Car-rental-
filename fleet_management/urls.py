from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Public website
    path("", include("website.urls")),

    # Internal management system
    path("dashboard/", include("dashboard.urls")),
    path("fleet/", include("fleet.urls")),
    path("rentals/", include("rentals.urls")),
    path("customers/", include("customers.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )