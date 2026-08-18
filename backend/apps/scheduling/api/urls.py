from django.urls import path

from .views import (
    SchedulingRunDetailView,
    SchedulingRunExecuteView,
    SchedulingRunListCreateView,
    SchedulingRunResultView,
)

urlpatterns = [
    path(
        "runs/",
        SchedulingRunListCreateView.as_view(),
        name="scheduling-run-list-create",
    ),
    path(
        "runs/<uuid:pk>/",
        SchedulingRunDetailView.as_view(),
        name="scheduling-run-detail",
    ),
    path(
        "runs/<uuid:pk>/execute/",
        SchedulingRunExecuteView.as_view(),
        name="scheduling-run-execute",
    ),
    path(
        "runs/<uuid:pk>/results/",
        SchedulingRunResultView.as_view(),
        name="scheduling-run-result",
    ),
]