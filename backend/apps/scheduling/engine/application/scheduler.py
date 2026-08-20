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

        solver_model = self.model_builder.build(problem)

        return self.solver.solve(
            problem=problem,
            solver_model=solver_model,
        )


def create_default_scheduler(
    *,
    time_limit_seconds: float = 30.0,
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
