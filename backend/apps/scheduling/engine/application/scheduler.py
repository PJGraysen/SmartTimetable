from __future__ import annotations

from dataclasses import dataclass

from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.objective import (
    BalancedTeacherWorkloadObjective,
    CompositeSolverObjective,
    SolverObjective,
    TeacherConsecutivePeriodObjective,
)
from apps.scheduling.engine.solver.result import SolverResult
from apps.scheduling.engine.solver.solver import CPSATSolver


@dataclass(slots=True)
class SchedulingService:
    """
    Application-level orchestration service for timetable generation.
    """

    model_builder: SolverModelBuilder
    solver: CPSATSolver

    def generate(
        self,
        problem: SchedulingProblem,
    ) -> SolverResult:
        """
        Generate a timetable for the supplied scheduling problem.
        """

        # --- Block-slot rotation (TEMPORARILY DISABLED 2026-09-25) ---
        # Rotation produces offsets that shift Form 4 blocks into
        # periods (P7/P8) that conflict with teacher availability.
        # Disabled until we can produce feasible rotations.
        # --- end block-slot rotation ---

        solver_model = self.model_builder.build(problem)

        # --- Diversity vs previous version (SmartTimetable Pro) ---
        # TEMPORARILY DISABLED 2026-09-25 — pending teacher-roster alignment
        # (backup has the full block; re-enable after base generation works)
        # --- end diversity ---

        return self.solver.solve(
            problem=problem,
            solver_model=solver_model,
        )


def create_default_scheduler(
    *,
    time_limit_seconds: float = 900.0,
    num_workers: int | None = None,
    objective: SolverObjective | None = None,
) -> SchedulingService:
    """
    Create the standard scheduling service configuration.

    The default scheduler combines the established workload/distribution
    objective with the teacher consecutive-period objective.
    """

    selected_objective = (
        objective
        if objective is not None
        else CompositeSolverObjective(
            objectives=(
                BalancedTeacherWorkloadObjective(),
                TeacherConsecutivePeriodObjective(),
            ),
        )
    )

    return SchedulingService(
        model_builder=SolverModelBuilder(
            objective=selected_objective,
        ),
        solver=CPSATSolver(
            time_limit_seconds=time_limit_seconds,
            num_workers=num_workers,
        ),
    )
