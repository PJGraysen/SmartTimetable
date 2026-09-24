from django.urls import path

from .views import (
    SchedulingRunDetailView,
    SchedulingRunExecuteView,
    SchedulingRunListCreateView,
    SchedulingRunResultView,
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
]