"""
Module-level API access middleware.

Blocks any API request whose URL prefix maps to a module the user does
not have. This is the last line of defence — even if a frontend route
slips through, the backend will refuse the data.
"""
import re
from django.http import JsonResponse


# Order matters — first match wins.
URL_MODULE_MAP = [
    ("/api/inventory/",  "inventory"),
    ("/api/scheduling/", "scheduling"),
    ("/api/academics/",  "academics"),
    ("/api/library/",    "library"),
    ("/api/platform/",   "platform"),
    ("/api/finance/",    "finance"),
    ("/api/ai/",         "aichat"),
]

# These prefixes must always be reachable (login, /me, notifications, docs).
PUBLIC_PREFIXES = (
    "/api/platform/auth/",        # login/logout/me
    "/api/notifications/",        # user's own notifications
    "/api/approvals/",            # user's own approvals
    "/api/schema/",
    "/api/docs/",
    "/api/redoc/",
    "/api/core/events/",          # school events — informational
)


class ModuleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""

        # Not an API call → let it through (admin, static, media, etc.)
        if not path.startswith("/api/"):
            return self.get_response(request)

        # Always-allowed paths
        for pp in PUBLIC_PREFIXES:
            if path.startswith(pp):
                return self.get_response(request)

        # Unauthenticated → let DRF return 401/403 naturally
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return self.get_response(request)

        # Superuser sees everything
        if user.is_superuser:
            return self.get_response(request)

        # Find the module this URL belongs to
        matched_module = None
        for prefix, module_name in URL_MODULE_MAP:
            if path.startswith(prefix):
                matched_module = module_name
                break

        if matched_module is None:
            return self.get_response(request)

        # Ask the role engine
        try:
            from apps.core.roles import modules_for_user
            user_modules = modules_for_user(user)
        except Exception:
            return self.get_response(request)

        if "*" in user_modules:
            return self.get_response(request)

        if matched_module in user_modules:
            return self.get_response(request)

        return JsonResponse(
            {"detail": f"You don't have access to the {matched_module} module."},
            status=403,
        )
