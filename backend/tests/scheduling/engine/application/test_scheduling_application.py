from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from apps.scheduling.engine.application.scheduling_application import (
    SchedulingApplicationService,
)
from apps.scheduling.engine.domain.enums import SolverStatus
from apps.scheduling.models import (
    SchedulingRunStatus,
    SolverStatus as DjangoSolverStatus,
)


@pytest.mark.django_db
def test_execute_marks_pending_run_running_before_execution(
    scheduling_run,
):
    scheduler = Mock()
    persistence = Mock()
    problem = Mock()

    solver_result = Mock()
    solver_result.status = SolverStatus.INFEASIBLE
    solver_result.statistics = SimpleNamespace(
        wall_time_seconds=1.25,
        branches=10,
        conflicts=2,
    )

    scheduler.generate.return_value = solver_result

    service = SchedulingApplicationService(
        scheduler=scheduler,
        persistence=persistence,
    )

    with patch(
        "apps.scheduling.engine.application.scheduling_application.load_scheduling_problem",
        return_value=problem,
    ) as loader:
        result = service.execute(
            scheduling_run=scheduling_run,
            version_name="Test Version",
            version_number=1,
        )

    scheduling_run.refresh_from_db()

    assert result.solver_result is solver_result
    assert result.persistence_result is None

    assert scheduling_run.status == SchedulingRunStatus.FAILED
    assert (
        scheduling_run.solver_status
        == DjangoSolverStatus.INFEASIBLE
    )

    loader.assert_called_once_with(
        term=scheduling_run.term,
    )

    scheduler.generate.assert_called_once_with(problem)

    persistence.persist.assert_not_called()


@pytest.mark.django_db
def test_execute_persists_successful_solver_result(
    scheduling_run,
):
    scheduler = Mock()
    persistence = Mock()
    problem = Mock()

    solver_result = Mock()
    solver_result.status = SolverStatus.FEASIBLE

    persistence_result = Mock()

    scheduler.generate.return_value = solver_result
    persistence.persist.return_value = persistence_result

    service = SchedulingApplicationService(
        scheduler=scheduler,
        persistence=persistence,
    )

    with patch(
        "apps.scheduling.engine.application.scheduling_application.load_scheduling_problem",
        return_value=problem,
    ) as loader:
        result = service.execute(
            scheduling_run=scheduling_run,
            version_name="Generated Version",
            version_number=1,
        )

    scheduling_run.refresh_from_db()

    assert result.solver_result is solver_result
    assert result.persistence_result is persistence_result

    loader.assert_called_once_with(
        term=scheduling_run.term,
    )

    scheduler.generate.assert_called_once_with(problem)

    persistence.persist.assert_called_once_with(
        scheduling_run=scheduling_run,
        solver_result=solver_result,
        version_name="Generated Version",
        version_number=1,
    )


@pytest.mark.django_db
def test_execute_accepts_optimal_solver_result(
    scheduling_run,
):
    scheduler = Mock()
    persistence = Mock()
    problem = Mock()

    solver_result = Mock()
    solver_result.status = SolverStatus.OPTIMAL

    persistence_result = Mock()

    scheduler.generate.return_value = solver_result
    persistence.persist.return_value = persistence_result

    service = SchedulingApplicationService(
        scheduler=scheduler,
        persistence=persistence,
    )

    with patch(
        "apps.scheduling.engine.application.scheduling_application.load_scheduling_problem",
        return_value=problem,
    ) as loader:
        result = service.execute(
            scheduling_run=scheduling_run,
            version_name="Optimal Version",
            version_number=1,
        )

    scheduling_run.refresh_from_db()

    assert result.solver_result is solver_result
    assert result.persistence_result is persistence_result

    loader.assert_called_once_with(
        term=scheduling_run.term,
    )

    scheduler.generate.assert_called_once_with(problem)

    persistence.persist.assert_called_once_with(
        scheduling_run=scheduling_run,
        solver_result=solver_result,
        version_name="Optimal Version",
        version_number=1,
    )


@pytest.mark.django_db
def test_execute_rejects_completed_run(
    scheduling_run,
):
    scheduling_run.status = SchedulingRunStatus.COMPLETED
    scheduling_run.save(update_fields=["status"])

    service = SchedulingApplicationService(
        scheduler=Mock(),
        persistence=Mock(),
    )

    with pytest.raises(ValueError, match="PENDING or RUNNING"):
        service.execute(
            scheduling_run=scheduling_run,
            version_name="Invalid Version",
            version_number=1,
        )