from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.scheduling.engine.domain.enums import SolverStatus
from apps.scheduling.models import (
    SchedulingRun,
    SchedulingRunStatus,
    SolverStatus as DjangoSolverStatus,
    TimetableVersion,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_list_scheduling_runs(api_client, scheduling_run):
    response = api_client.get(
        "/api/scheduling/runs/",
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 1

    run_data = data[0]

    assert run_data["id"] == str(scheduling_run.id)
    assert run_data["term"] == str(scheduling_run.term.id)
    assert run_data["term_name"] == scheduling_run.term.name
    assert run_data["status"] == SchedulingRunStatus.PENDING
    assert run_data["status_display"] == "Pending"


@pytest.mark.django_db
def test_create_scheduling_run(
    api_client,
    scheduling_run,
):
    term = scheduling_run.term

    scheduling_run.delete()

    response = api_client.post(
        "/api/scheduling/runs/",
        {
            "term": str(term.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["term"] == str(term.id)
    assert data["term_name"] == term.name
    assert data["status"] == SchedulingRunStatus.PENDING

    created_run = SchedulingRun.objects.get(
        id=data["id"],
    )

    assert created_run.term_id == term.id
    assert created_run.status == SchedulingRunStatus.PENDING


@pytest.mark.django_db
def test_create_scheduling_run_requires_term(
    api_client,
):
    response = api_client.post(
        "/api/scheduling/runs/",
        {},
        format="json",
    )

    assert response.status_code == (
        status.HTTP_400_BAD_REQUEST
    )

    data = response.json()

    assert "term" in data


@pytest.mark.django_db
def test_retrieve_scheduling_run(
    api_client,
    scheduling_run,
):
    response = api_client.get(
        f"/api/scheduling/runs/{scheduling_run.id}/",
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == str(scheduling_run.id)
    assert data["term"] == str(scheduling_run.term.id)
    assert data["term_name"] == scheduling_run.term.name
    assert data["status"] == SchedulingRunStatus.PENDING


@pytest.mark.django_db
def test_retrieve_nonexistent_scheduling_run(
    api_client,
):
    response = api_client.get(
        "/api/scheduling/runs/"
        "00000000-0000-0000-0000-000000000000/",
    )

    assert response.status_code == (
        status.HTTP_404_NOT_FOUND
    )


@pytest.mark.django_db
def test_execute_scheduling_run(
    api_client,
    scheduling_run,
):
    solver_result = Mock()
    solver_result.status = SolverStatus.OPTIMAL

    persistence_result = Mock()

    service_result = Mock()
    service_result.scheduling_run = scheduling_run
    service_result.solver_result = solver_result
    service_result.persistence_result = persistence_result

    with patch(
        "apps.scheduling.api.views.SchedulingApplicationService",
    ) as service_class:
        service = service_class.return_value

        service.execute.return_value = service_result

        response = api_client.post(
            f"/api/scheduling/runs/{scheduling_run.id}/execute/",
            {
                "version_name": "API Test Timetable",
                "version_number": 1,
            },
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK

    service.execute.assert_called_once_with(
        scheduling_run=scheduling_run,
        version_name="API Test Timetable",
        version_number=1,
    )


@pytest.mark.django_db
def test_execute_scheduling_run_rejects_completed_run(
    api_client,
    scheduling_run,
):
    scheduling_run.status = (
        SchedulingRunStatus.COMPLETED
    )

    scheduling_run.save(
        update_fields=["status"],
    )

    response = api_client.post(
        f"/api/scheduling/runs/{scheduling_run.id}/execute/",
        {
            "version_name": "Invalid Execution",
            "version_number": 1,
        },
        format="json",
    )

    assert response.status_code == (
        status.HTTP_409_CONFLICT
    )

    data = response.json()

    assert "Only PENDING or RUNNING" in data["detail"]


@pytest.mark.django_db
def test_execute_scheduling_run_validation_error(
    api_client,
    scheduling_run,
):
    response = api_client.post(
        f"/api/scheduling/runs/{scheduling_run.id}/execute/",
        {
            "version_name": "",
            "version_number": 0,
        },
        format="json",
    )

    assert response.status_code == (
        status.HTTP_400_BAD_REQUEST
    )


@pytest.mark.django_db
def test_execute_scheduling_run_handles_value_error(
    api_client,
    scheduling_run,
):
    with patch(
        "apps.scheduling.api.views.SchedulingApplicationService",
    ) as service_class:
        service = service_class.return_value

        service.execute.side_effect = ValueError(
            "Scheduling request is invalid.",
        )

        response = api_client.post(
            f"/api/scheduling/runs/{scheduling_run.id}/execute/",
            {
                "version_name": "Invalid Request",
                "version_number": 1,
            },
            format="json",
        )

    assert response.status_code == (
        status.HTTP_409_CONFLICT
    )

    data = response.json()

    assert data["detail"] == (
        "Scheduling request is invalid."
    )


@pytest.mark.django_db
def test_execute_scheduling_run_handles_unexpected_error(
    api_client,
    scheduling_run,
):
    with patch(
        "apps.scheduling.api.views.SchedulingApplicationService",
    ) as service_class:
        service = service_class.return_value

        service.execute.side_effect = RuntimeError(
            "Unexpected scheduling failure.",
        )

        response = api_client.post(
            f"/api/scheduling/runs/{scheduling_run.id}/execute/",
            {
                "version_name": "Failure Test",
                "version_number": 1,
            },
            format="json",
        )

    assert response.status_code == (
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    data = response.json()

    assert data["detail"] == (
        "Scheduling execution failed."
    )

    assert data["error"] == (
        "Unexpected scheduling failure."
    )


@pytest.mark.django_db
def test_get_scheduling_run_results_without_timetable(
    api_client,
    scheduling_run,
):
    response = api_client.get(
        f"/api/scheduling/runs/{scheduling_run.id}/results/",
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == str(scheduling_run.id)
    assert data["term"] == str(scheduling_run.term.id)
    assert data["timetable_version"] is None
    assert data["status"] == SchedulingRunStatus.PENDING


@pytest.mark.django_db
def test_get_scheduling_run_results_with_timetable(
    api_client,
    scheduling_run,
):
    timetable_version = TimetableVersion.objects.create(
        term=scheduling_run.term,
        name="API Results Test",
        version_number=1,
        is_published=False,
        is_active=True,
    )

    scheduling_run.timetable_version = (
        timetable_version
    )

    scheduling_run.status = (
        SchedulingRunStatus.COMPLETED
    )

    scheduling_run.solver_status = (
        DjangoSolverStatus.OPTIMAL
    )

    scheduling_run.save(
        update_fields=[
            "timetable_version",
            "status",
            "solver_status",
        ],
    )

    response = api_client.get(
        f"/api/scheduling/runs/{scheduling_run.id}/results/",
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == str(scheduling_run.id)
    assert data["term"] == str(scheduling_run.term.id)
    assert data["status"] == (
        SchedulingRunStatus.COMPLETED
    )
    assert data["solver_status"] == (
        DjangoSolverStatus.OPTIMAL
    )

    timetable_data = data["timetable_version"]

    assert timetable_data["id"] == (
        str(timetable_version.id)
    )

    assert timetable_data["term"] == (
        str(scheduling_run.term.id)
    )

    assert timetable_data["name"] == (
        "API Results Test"
    )

    assert timetable_data["version_number"] == 1
    assert timetable_data["entries_count"] == 0
    assert timetable_data["entries"] == []


@pytest.mark.django_db
def test_get_results_for_nonexistent_scheduling_run(
    api_client,
):
    response = api_client.get(
        "/api/scheduling/runs/"
        "00000000-0000-0000-0000-000000000000/"
        "results/",
    )

    assert response.status_code == (
        status.HTTP_404_NOT_FOUND
    )