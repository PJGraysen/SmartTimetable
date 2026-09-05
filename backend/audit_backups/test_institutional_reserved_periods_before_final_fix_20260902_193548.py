from dataclasses import replace

from apps.scheduling.engine.domain.enums import DayOfWeek
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver

from tests.scheduling.engine.solver.test_solver_constraints import (
    build_constraint_problem,
)


def _solve(problem):
    solver_model = SolverModelBuilder().build(problem)

    return CPSATSolver(
        time_limit_seconds=10.0,
        num_workers=1,
    ).solve(
        problem=problem,
        solver_model=solver_model,
    )


def _monday_p1_slot(problem):
    matches = tuple(
        slot
        for slot in problem.slots
        if slot.day == DayOfWeek.MONDAY
        and slot.period_number == 1
    )

    assert len(matches) == 1, (
        "Expected exactly one Monday P1 slot, "
        f"found {len(matches)}."
    )

    return matches[0]


def test_monday_period_one_is_reserved_for_assembly():
    """
    Monday P1 is institutionally reserved for Assembly and therefore
    cannot contain a normal lesson.
    """
    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    result = _solve(problem)

    assert result.is_successful

    assert all(
        not (
            assignment.day == DayOfWeek.MONDAY
            and assignment.period_number == 1
        )
        for assignment in result.assignments
    )


def test_monday_period_one_only_is_infeasible():
    """
    If Monday P1 is the only available slot, the normal lesson must
    be infeasible because Monday P1 is reserved for Assembly.
    """
    base_problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    monday_p1_slot = _monday_p1_slot(base_problem)

    room_availability = tuple(
        availability
        for availability in base_problem.room_availability
        if (
            availability.room_id == base_problem.rooms[0].id
            and availability.period_id == monday_p1_slot.period_id
            and availability.day == DayOfWeek.MONDAY
        )
    )

    assert len(room_availability) == 1, (
        "Expected exactly one room-availability record for Monday P1, "
        f"found {len(room_availability)}."
    )

    problem = replace(
        base_problem,
        slots=(monday_p1_slot,),
        room_availability=room_availability,
    )

    result = _solve(problem)

    assert result.status.name == "INFEASIBLE"