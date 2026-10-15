from django.conf import settings
from django.contrib.auth.views import redirect_to_login


class InternalAuthenticationMiddleware:
    """
    Require authentication for internal management pages.

    Public website pages remain accessible without logging in.
    """

    INTERNAL_PREFIXES = (
        "/dashboard/",
        "/fleet/",
        "/customers/",
        "/rentals/",
        "/payments/",
        "/agreements/",
        "/maintenance/",
        "/returns/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        requires_login = any(
            path == prefix.rstrip("/")
            or path.startswith(prefix)
            for prefix in self.INTERNAL_PREFIXES
        )

        if requires_login and not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                settings.LOGIN_URL,
            )

        return self.get_response(request)