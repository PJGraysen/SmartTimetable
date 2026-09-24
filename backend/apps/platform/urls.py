from django.urls import path

from . import views

urlpatterns = [
    path("auth/login/", views.login_view, name="platform-login"),
    path("auth/logout/", views.logout_view, name="platform-logout"),
    path("auth/me/", views.me_view, name="platform-me"),
    path("applications/", views.applications_view, name="platform-applications"),
]



# ---------------------------------------------------------------------
# Platform admin console endpoints (added 2026-09-17)
# ---------------------------------------------------------------------
from django.urls import path as _apath
from apps.platform.admin_views import (
    AdminUsersView, AdminUserDetailView, AdminUserResetPasswordView,
    AdminGroupsView, AdminGroupDetailView,
    AdminHealthView, AdminWarningsView,
)

_admin_patterns = [
    _apath("admin/users/",                        AdminUsersView.as_view(),           name="admin-users"),
    _apath("admin/users/<int:user_id>/",          AdminUserDetailView.as_view(),      name="admin-user-detail"),
    _apath("admin/users/<int:user_id>/reset-password/", AdminUserResetPasswordView.as_view(), name="admin-user-reset"),
    _apath("admin/groups/",                       AdminGroupsView.as_view(),          name="admin-groups"),
    _apath("admin/groups/<int:group_id>/",        AdminGroupDetailView.as_view(),     name="admin-group-detail"),
    _apath("admin/health/",                       AdminHealthView.as_view(),          name="admin-health"),
    _apath("admin/warnings/",                     AdminWarningsView.as_view(),        name="admin-warnings"),
]

try:
    urlpatterns = list(urlpatterns) + _admin_patterns
except NameError:
    urlpatterns = _admin_patterns



from rest_framework.routers import DefaultRouter as _DR_T
from apps.platform.admin_views import TeacherAdminViewSet as _TAVS
_t_router = _DR_T()
_t_router.register(r"admin/teachers", _TAVS, basename="admin-teacher")
try:
    urlpatterns = list(urlpatterns) + list(_t_router.urls)
except NameError:
    urlpatterns = list(_t_router.urls)
