from apps.scheduling.engine.domain.enums import DayOfWeek
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver

from tests.scheduling.engine.solver.test_solver_constraints import (
    build_constraint_problem,
)


def solve_problem(problem):
    solver_model = SolverModelBuilder().build(problem)

    return CPSATSolver(
        time_limit_seconds=10.0,
        num_workers=1,
    ).solve(
        problem=problem,
        solver_model=solver_model,
    )


def test_monday_period_one_is_reserved_for_assembly():
    """
    Monday P1 is reserved for Assembly and therefore cannot contain
    a teaching assignment.
    """

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    monday_p1 = problem.periods[0]

    result = solve_problem(problem)

    assert result.is_successful
    assert len(result.assignments) == 1

    assignment = result.assignments[0]

    assert not (
        assignment.day == DayOfWeek.MONDAY
        and assignment.period_id == monday_p1.id
    )


def test_monday_period_one_only_is_infeasible():
    """
    When Monday P1 is the only available slot, the lesson is infeasible
    because Monday P1 is reserved for Assembly.
    """

    base_problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    monday_p1 = base_problem.periods[0]

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
        slots=(
            base_problem.slots[0],
        ),
    )

    result = solve_problem(problem)

    assert result.status.name == "INFEASIBLE"
    assert not result.is_successful