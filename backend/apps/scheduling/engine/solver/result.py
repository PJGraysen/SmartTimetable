from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from apps.scheduling.engine.domain.entities import SchedulingAssignment
from apps.scheduling.engine.domain.enums import SolverStatus


@dataclass(frozen=True, slots=True)
class SolverStatistics:
    """Execution statistics returned by the solver."""

    wall_time_seconds: float = 0.0
    branches: int = 0
    conflicts: int = 0
    objective_value: Optional[float] = None


@dataclass(frozen=True, slots=True)
class SolverResult:
    """Immutable result of a scheduling solver execution."""

    status: SolverStatus
    assignments: tuple[SchedulingAssignment, ...] = ()
    statistics: SolverStatistics = SolverStatistics()
    error_message: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Whether the solver produced a usable timetable."""
        return self.status in {
            SolverStatus.FEASIBLE,
            SolverStatus.OPTIMAL,
        }

    @property
    def is_optimal(self) -> bool:
        """Whether CP-SAT proved the solution optimal."""
        return self.status == SolverStatus.OPTIMAL