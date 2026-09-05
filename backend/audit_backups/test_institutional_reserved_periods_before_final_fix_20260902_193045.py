from dataclasses import replace

from apps.scheduling.engine.domain.enums import DayOfWeek
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver

from tests.scheduling.engine.solver.test_solver_constraints import (
    build_constraint_problem,
)


def test_monday_period_one_is_reserved_for_assembly():
    """
    Monday P1 must never be used for a normal lesson because it is
    institutionally reserved for Assembly.
    """
    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    model = SolverModelBuilder(problem).build()
    result = CPSATSolver(time_limit_seconds=10).solve(model)

    assert result.status.name == "OPTIMAL"
    assert result.assignments

    for assignment in result.assignments:
        assert not (
            assignment.day == DayOfWeek.MONDAY
            and assignment.period_number == 1
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

    monday_p1_period = base_problem.periods[0]
    monday_p1_slot = base_problem.slots[0]

    # The original fixture contains availability records for every period.
    # Once the problem is reduced to a single slot, retain only the matching
    # room-availability record so SchedulingProblem reference validation
    # remains internally consistent.
    room_availability = tuple(
        availability
        for availability in base_problem.room_availability
        if availability.period_id == monday_p1_period.id
    )

    problem = replace(
        base_problem,
        slots=(monday_p1_slot,),
        room_availability=room_availability,
    )

    model = SolverModelBuilder(problem).build()
    result = CPSATSolver(time_limit_seconds=10).solve(model)

    assert result.status.name == "INFEASIBLE"