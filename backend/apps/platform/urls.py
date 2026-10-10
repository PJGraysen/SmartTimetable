from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views
from .admin_views import (
    AdminUsersView, AdminUserDetailView, AdminUserResetPasswordView,
    AdminGroupsView, AdminGroupDetailView,
    AdminHealthView, AdminWarningsView,
    TeacherAdminViewSet,
)
from apps.platform.teacher_merge import (
    teacher_scan_duplicates, teacher_merge,
)
from apps.platform.teacher_extra import (
    teacher_assignments, teacher_assign, teacher_unassign,
    teacher_create, teacher_update_profile, teacher_bulk_assign,
    teacher_delete, teacher_free_afternoon, teacher_retire, teacher_reactivate,
    subjects_list as admin_subjects_list,
    classes_list as admin_classes_list,
)

# ------------------------------------------------------------------
# CUSTOM teacher routes MUST be evaluated BEFORE the router, otherwise
# admin/teachers/create/ is captured by admin/teachers/<pk>/.
# ------------------------------------------------------------------
custom_teacher_routes = [
    path("admin/teachers/duplicates/", teacher_scan_duplicates, name="teacher-scan-duplicates"),
    path("admin/teachers/merge/", teacher_merge, name="teacher-merge"),
    path("admin/teachers/create/", teacher_create, name="teacher-create"),
    path("admin/teachers/<uuid:pk>/delete/", teacher_delete, name="teacher-delete"),
    path("admin/teachers/<uuid:pk>/assignments/", teacher_assignments, name="teacher-assignments"),
    path("admin/teachers/<uuid:pk>/assign/", teacher_assign, name="teacher-assign"),
    path("admin/teachers/<uuid:pk>/assign/<uuid:lr_id>/", teacher_unassign, name="teacher-unassign"),
    path("admin/teachers/<uuid:pk>/profile/", teacher_update_profile, name="teacher-update-profile"),
    path("admin/teachers/<uuid:pk>/bulk-assign/", teacher_bulk_assign, name="teacher-bulk-assign"),
    path("admin/teachers/<uuid:pk>/free-afternoon/", teacher_free_afternoon, name="teacher-free-afternoon"),
    path("admin/teachers/<uuid:pk>/retire/", teacher_retire, name="teacher-retire"),
    path("admin/teachers/<uuid:pk>/reactivate/", teacher_reactivate, name="teacher-reactivate"),
    path("admin/subjects/", admin_subjects_list, name="admin-subjects"),
    path("admin/classes/", admin_classes_list, name="admin-classes"),
]

router = SimpleRouter()
router.register(r"admin/teachers", TeacherAdminViewSet, basename="admin-teacher")

urlpatterns = [
    # Base platform
    path("auth/login/", views.login_view, name="platform-login"),
    path("auth/verify/", views.verify_login_view, name="platform-verify"),
    path("auth/resend-code/", views.resend_code_view, name="platform-resend-code"),
    path("auth/logout/", views.logout_view, name="platform-logout"),
    path("auth/me/", views.me_view, name="platform-me"),
    path("applications/", views.applications_view, name="platform-applications"),

    # Admin console
    path("admin/users/", AdminUsersView.as_view(), name="admin-users"),
    path("admin/users/<int:user_id>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/users/<int:user_id>/reset-password/", AdminUserResetPasswordView.as_view(), name="admin-user-reset"),
    path("admin/groups/", AdminGroupsView.as_view(), name="admin-groups"),
    path("admin/groups/<int:group_id>/", AdminGroupDetailView.as_view(), name="admin-group-detail"),
    path("admin/health/", AdminHealthView.as_view(), name="admin-health"),
    path("admin/warnings/", AdminWarningsView.as_view(), name="admin-warnings"),

    # CUSTOM routes FIRST
    *custom_teacher_routes,

    # Router LAST (only matches UUID pk now)
    *router.urls,
]
