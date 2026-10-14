from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("admin/", admin.site.urls),

    # Public website
    path("", include("website.urls")),

    # Authentication
   path(
    "login/",
    auth_views.LoginView.as_view(
        template_name="registration/login.html"
    ),
    name="login_alias",
),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    # Internal system
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