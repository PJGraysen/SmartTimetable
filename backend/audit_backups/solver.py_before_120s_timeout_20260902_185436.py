from __future__ import annotations

from typing import Optional

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
        time_limit_seconds: float = 30.0,
        num_workers: Optional[int] = None,
    ) -> None:
        self.time_limit_seconds = time_limit_seconds
        self.num_workers = num_workers

    def solve(
        self,
        problem: SchedulingProblem,
        solver_model: SolverModel,
    ) -> SolverResult:
        """
        Solve the supplied scheduling model.
        """

        solver = cp_model.CpSolver()

        solver.parameters.max_time_in_seconds = (
            self.time_limit_seconds
        )

        if self.num_workers is not None:
            solver.parameters.num_workers = self.num_workers

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

        assignments: list[SchedulingAssignment] = []

        for variable in solver_model.variables:

            if solver.value(variable.variable) != 1:
                continue

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
                    room_id=variable.room_id,
                )
            )

        return tuple(assignments)


def problem_day(value: str):
    """
    Convert a serialized day value back to the domain enum.
    """

    from apps.scheduling.engine.domain.enums import DayOfWeek

    return DayOfWeek(value)
