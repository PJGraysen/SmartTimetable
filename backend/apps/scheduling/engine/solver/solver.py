from __future__ import annotations

from collections import defaultdict
from typing import Optional
from uuid import UUID

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.entities import (
    SchedulingAssignment,
)

from apps.scheduling.engine.domain.problem import SchedulingProblem

from apps.scheduling.engine.domain.enums import SolverStatus
from apps.scheduling.engine.solver.infeasibility_diagnostics import (
    analyze_infeasibility,
)
from apps.scheduling.engine.solver.model import SolverModel
from apps.scheduling.engine.solver.variables import AssignmentVariable
from apps.scheduling.engine.solver.result import (
    SolverResult,
    SolverStatistics,
)


class CPSATSolver:
    """
    Executes a SolverModel using Google's CP-SAT solver.

    The solver itself does not know anything about Django.
    It receives a validated SchedulingProblem through SolverModel.

    When CP-SAT proves the model infeasible, the solver also runs
    the domain-level infeasibility diagnostic engine against the
    original SchedulingProblem and exposes the resulting report
    through SolverResult.error_message.
    """

    def __init__(
        self,
        *,
        time_limit_seconds: float = 900.0,
        num_workers: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> None:
        self.time_limit_seconds = time_limit_seconds
        self.num_workers = num_workers
        self.seed = seed

    def _resolve_seed(self) -> int:
        """Deterministic CP-SAT seed.

        Resolution order:
          1. explicit self.seed (constructor arg)
          2. Django setting TIMETABLE_SOLVER_SEED:
               -1 -> legacy random-per-run (diversity mode)
                0 -> deterministic (default)
                N -> deterministic with fixed seed N
          3. fallback: 0 (deterministic)
        """
        if self.seed is not None:
            return int(self.seed) & 0x7FFFFFFF
        try:
            from django.conf import settings
            value = getattr(settings, "TIMETABLE_SOLVER_SEED", 0)
        except Exception:
            value = 0
        if value == -1:
            import os as _oo
            return int.from_bytes(_oo.urandom(4), "little") & 0x7FFFFFFF
        return int(value) & 0x7FFFFFFF

    def solve(
        self,
        problem: SchedulingProblem,
        solver_model: SolverModel,
    ) -> SolverResult:
        """
        Solve the supplied scheduling model.
        """

        solver = cp_model.CpSolver()



        solver.parameters.random_seed = self._resolve_seed()


        solver.parameters.num_search_workers = 1

        solver.parameters.max_time_in_seconds = (
            self.time_limit_seconds
        )

        if self.num_workers is not None:
            solver.parameters.num_search_workers = self.num_workers

        try:
            status = solver.solve(solver_model.model)

            solver_status = self._map_status(status)

            assignments: tuple[SchedulingAssignment, ...] = ()

            if status in (
                cp_model.FEASIBLE,
                cp_model.OPTIMAL,
            ):
                assignments = self._extract_assignments(
                    problem=problem,
                    solver_model=solver_model,
                    solver=solver,
                )

            statistics = SolverStatistics(
                wall_time_seconds=solver.wall_time,
                branches=solver.num_branches,
                conflicts=solver.num_conflicts,
                objective_value=(
                    solver.objective_value
                    if status in (
                        cp_model.FEASIBLE,
                        cp_model.OPTIMAL,
                    )
                    else None
                ),
            )

            error_message: str | None = None

            if status == cp_model.INFEASIBLE:
                diagnostic_report = analyze_infeasibility(
                    problem,
                )

                error_message = diagnostic_report.format_message()

            return SolverResult(
                status=solver_status,
                assignments=assignments,
                statistics=statistics,
                error_message=error_message,
            )

        except Exception as exc:
            return SolverResult(
                status=SolverStatus.FAILED,
                error_message=str(exc),
            )

    @staticmethod
    def _map_status(status: int) -> SolverStatus:
        """Map CP-SAT status codes into our domain enum."""

        mapping = {
            cp_model.UNKNOWN: SolverStatus.UNKNOWN,
            cp_model.MODEL_INVALID: SolverStatus.MODEL_INVALID,
            cp_model.FEASIBLE: SolverStatus.FEASIBLE,
            cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
            cp_model.OPTIMAL: SolverStatus.OPTIMAL,
        }

        return mapping.get(
            status,
            SolverStatus.FAILED,
        )

    @staticmethod
    def _extract_assignments(
        *,
        problem: SchedulingProblem,
        solver_model: SolverModel,
        solver: cp_model.CpSolver,
    ) -> tuple[SchedulingAssignment, ...]:
        """Convert true CP-SAT variables into domain assignments."""
        selected_variables = [
            (index, variable)
            for index, variable in enumerate(solver_model.variables)
            if solver.value(variable.variable) == 1
        ]
        variables_by_slot: dict[
            tuple[str, UUID],
            list[tuple[int, AssignmentVariable]],
        ] = defaultdict(list)

        for index, variable in selected_variables:
            variables_by_slot[
                (
                    variable.day,
                    variable.period_id,
                )
            ].append(
                (
                    index,
                    variable,
                )
            )

        room_ids_by_variable_index: dict[int, UUID] = {}

        for slot_key, slot_variables in variables_by_slot.items():
            available_room_ids = (
                solver_model.available_room_ids_by_slot.get(slot_key)
            )

            if available_room_ids is None:
                raise ValueError(
                    "No room candidates were recorded for selected "
                    f"timetable slot {slot_key!r}."
                )

            if len(slot_variables) > len(available_room_ids):
                raise ValueError(
                    "Selected lessons exceed available rooms for "
                    f"timetable slot {slot_key!r}."
                )

            for (
                index,
                _variable,
            ), room_id in zip(
                sorted(
                    slot_variables,
                    key=lambda item: (
                        str(item[1].instructional_group_id),
                        str(item[1].lesson_requirement_id),
                        str(item[1].teacher_id),
                    ),
                ),
                available_room_ids,
            ):
                room_ids_by_variable_index[index] = room_id

        assignments: list[SchedulingAssignment] = []

        for index, variable in selected_variables:
            assignments.append(
                SchedulingAssignment(
                    lesson_requirement_id=(
                        variable.lesson_requirement_id
                    ),
                    teacher_id=variable.teacher_id,
                    instructional_group_id=(
                        variable.instructional_group_id
                    ),
                    period_id=variable.period_id,
                    day=problem_day(variable.day),
                    room_id=room_ids_by_variable_index[index],
                )
            )

        return tuple(assignments)


def problem_day(value: str):
    """
    Convert a serialized day value back to the domain enum.
    """

    from apps.scheduling.engine.domain.enums import DayOfWeek

    return DayOfWeek(value)
