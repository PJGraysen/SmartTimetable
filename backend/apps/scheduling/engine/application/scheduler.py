from __future__ import annotations

from dataclasses import dataclass

from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.result import SolverResult
from apps.scheduling.engine.solver.solver import CPSATSolver


@dataclass(slots=True)
class SchedulingService:
    """
    Application-level orchestration service for timetable generation.

    This service coordinates the domain problem, CP-SAT model builder,
    and solver without knowing anything about Django persistence.

    The service deliberately does not create TimetableVersion or
    TimetableEntry records. Persistence belongs to a separate
    infrastructure/application boundary.
    """

    model_builder: SolverModelBuilder
    solver: CPSATSolver

    def generate(
        self,
        problem: SchedulingProblem,
    ) -> SolverResult:
        """
        Generate a timetable for the supplied scheduling problem.

        The problem is expected to have already passed its domain-level
        structural validation.
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
) -> SchedulingService:
    """
    Create the standard scheduling service configuration.
    """

    return SchedulingService(
        model_builder=SolverModelBuilder(),
        solver=CPSATSolver(
            time_limit_seconds=time_limit_seconds,
            num_workers=num_workers,
        ),
    )