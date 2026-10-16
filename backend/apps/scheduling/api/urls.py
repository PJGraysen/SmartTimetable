from apps.scheduling.api.scope_view import SchedulingScopeListView
from apps.scheduling.api.notifications_view import SchedulingNotificationsView
from apps.scheduling.api.drift_view import SchedulingDriftView
from django.urls import path

from .views import (
    SchedulingProposalApplyView,
    PreflightCheckView,
    SchedulingRunDetailView,
    SchedulingRunExecuteView,
    SchedulingRunListCreateView,
    SchedulingRunResultView,
    SchedulingRuleConfigView,
    SchedulingDashboardView,
    SchedulingRunApproveView,
    SchedulingRunUnapproveView,
    SchedulingRunReportView,
    SchedulingErrorReportView,
    SchedulingErrorListView,
    SchedulingResolveValidationView,
    SchedulingRunDiscardView,
)

urlpatterns = [
    path("dashboard/", SchedulingDashboardView.as_view(), name="scheduling-dashboard"),
    path("runs/", SchedulingRunListCreateView.as_view(), name="scheduling-run-list-create"),
    path("runs/<uuid:pk>/", SchedulingRunDetailView.as_view(), name="scheduling-run-detail"),
    path("runs/<uuid:pk>/execute/", SchedulingRunExecuteView.as_view(), name="scheduling-run-execute"),
    path("runs/<uuid:pk>/results/", SchedulingRunResultView.as_view(), name="scheduling-run-result"),
    path("runs/<uuid:pk>/report/", SchedulingRunReportView.as_view(), name="scheduling-run-report"),
    path("runs/<uuid:pk>/approve/", SchedulingRunApproveView.as_view(), name="scheduling-run-approve"),
    path("runs/<uuid:pk>/unapprove/", SchedulingRunUnapproveView.as_view(), name="scheduling-run-unapprove"),
path(
    "runs/<uuid:pk>/discard/",
    SchedulingRunDiscardView.as_view(),
    name="scheduling-run-discard",
),
    path(
        "runs/<uuid:run_id>/validation/<uuid:validation_id>/resolve/",
        SchedulingResolveValidationView.as_view(),
        name="scheduling-resolve-validation",
    ),
    path("errors/report/", SchedulingErrorReportView.as_view(), name="scheduling-error-report"),
    path("errors/", SchedulingErrorListView.as_view(), name="scheduling-error-list"),
    path("scopes/", SchedulingScopeListView.as_view(), name="scheduling-scope-list"),
    path("drift/", SchedulingDriftView.as_view(), name="scheduling-drift"),
    path("notifications/", SchedulingNotificationsView.as_view(), name="scheduling-notifications"),
]


# ---------------------------------------------------------------------
# Duty Roster (Session 3)
# ---------------------------------------------------------------------
from django.urls import path
from apps.scheduling.duty_api import (
    duty_roster, duty_assign, duty_unassign, teacher_duty_preference,
    duty_auto_rotate,
)

urlpatterns += [
    path("duty-roster/", duty_roster, name="duty-roster"),
    path("duty-roster/assign/", duty_assign, name="duty-assign"),
    path("duty-roster/<uuid:pk>/", duty_unassign, name="duty-unassign"),
    path("duty-roster/preference/<uuid:teacher_id>/", teacher_duty_preference, name="teacher-duty-preference"),
    path("duty-roster/auto-rotate/", duty_auto_rotate, name="duty-auto-rotate"),
]

urlpatterns += [
    path(
        "rule-config/",
        SchedulingRuleConfigView.as_view(),
        name="scheduling-rule-config",
    ),
]
urlpatterns += [
    path(
        "preflight/",
        PreflightCheckView.as_view(),
        name="scheduling-preflight",
    ),
]
urlpatterns += [
    path(
        "proposals/apply/",
        SchedulingProposalApplyView.as_view(),
        name="scheduling-proposal-apply",
    ),
]
