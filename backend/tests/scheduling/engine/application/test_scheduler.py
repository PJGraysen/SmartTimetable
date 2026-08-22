from unittest.mock import Mock

from apps.scheduling.engine.application.scheduler import (
    SchedulingService,
    create_default_scheduler,
)
from apps.scheduling.engine.domain.enums import SolverStatus
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.result import SolverResult
from apps.scheduling.engine.solver.solver import CPSATSolver


def make_empty_problem() -> SchedulingProblem:
    """
    Create the smallest structurally valid scheduling problem.

    There are no active teachers, so the mandatory free-afternoon
    requirement has no active teachers to validate.
    """

    return SchedulingProblem.from_iterables(
        periods=[],
        teachers=[],
        instructional_groups=[],
        rooms=[],
        lesson_requirements=[],
        teacher_assignments=[],
        teacher_availability=[],
        teacher_free_afternoons=[],
        room_availability=[],
        slots=[],
    )


def test_generate_builds_model_and_delegates_to_solver():
    problem = make_empty_problem()

    expected_result = SolverResult(
        status=SolverStatus.OPTIMAL,
    )

    model_builder = Mock()
    solver = Mock()

    model = object()

    model_builder.build.return_value = model
    solver.solve.return_value = expected_result

    service = SchedulingService(
        model_builder=model_builder,
        solver=solver,
    )

    result = service.generate(problem)

    assert result is expected_result

    model_builder.build.assert_called_once_with(problem)

    solver.solve.assert_called_once_with(
        problem=problem,
        solver_model=model,
    )


def test_create_default_scheduler_uses_standard_components():
    service = create_default_scheduler(
        time_limit_seconds=15.0,
        num_workers=2,
    )

    assert isinstance(
        service.model_builder,
        SolverModelBuilder,
    )

    assert isinstance(
        service.solver,
        CPSATSolver,
    )

    assert service.solver.time_limit_seconds == 15.0
    assert service.solver.num_workers == 2