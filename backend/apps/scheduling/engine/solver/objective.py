from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.variables import AssignmentVariable


@dataclass(frozen=True, slots=True)
class ObjectiveTerm:
    """
    One weighted optimization term.

    Positive weights represent penalties because the objective is
    minimized by CP-SAT.
    """

    name: str
    expression: object
    weight: int = 1

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "Objective term name cannot be empty."
            )

        if self.weight <= 0:
            raise ValueError(
                "Objective term weight must be greater than zero."
            )


class SolverObjective(Protocol):
    """
    Runtime contract for solver objectives.
    """

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        """Apply the objective to a CP-SAT model."""
        ...


@dataclass(slots=True)
class SchedulingObjective:
    """
    Collection of weighted timetable optimization penalties.
    """

    terms: list[ObjectiveTerm]

    def __init__(
        self,
        terms: tuple[ObjectiveTerm, ...] | list[ObjectiveTerm] = (),
    ) -> None:
        self.terms = list(terms)

    @property
    def is_empty(self) -> bool:
        return not self.terms

    def names(self) -> tuple[str, ...]:
        return tuple(term.name for term in self.terms)

    def expression(self) -> object:
        if self.is_empty:
            return 0

        return sum(
            term.expression * term.weight
            for term in self.terms
        )

    def add_penalty(
        self,
        *,
        name: str,
        expression: object,
        weight: int = 1,
    ) -> None:
        self.terms.append(
            ObjectiveTerm(
                name=name,
                expression=expression,
                weight=weight,
            )
        )

    def extend(
        self,
        terms: tuple[ObjectiveTerm, ...] | list[ObjectiveTerm],
    ) -> None:
        for term in terms:
            if not isinstance(term, ObjectiveTerm):
                raise TypeError(
                    "SchedulingObjective.extend expects "
                    "ObjectiveTerm instances."
                )

        self.terms.extend(terms)

    def apply(
        self,
        model: cp_model.CpModel,
        *,
        problem: SchedulingProblem | None = None,
        variables: tuple[AssignmentVariable, ...] = (),
    ) -> None:
        if self.is_empty:
            return

        model.minimize(self.expression())


class NoOpSolverObjective:
    """
    Neutral objective.

    Leaves the model as a pure feasibility problem.
    """

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        return None


@dataclass(slots=True)
class BalancedTeacherWorkloadObjective:
    """
    Soft objective that distributes each teacher's lessons across days.

    For every active teacher, an auxiliary CP-SAT variable represents
    that teacher's maximum number of lessons on any one day.

    The objective minimizes the sum of those maximum daily workloads.

    This deliberately remains a soft objective. It never makes a
    timetable infeasible merely because workload cannot be perfectly
    balanced.
    """

    weight: int = 1

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                "Teacher workload objective weight must be greater than zero."
            )

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        variables_by_teacher_day: dict[
            tuple[object, str],
            list[cp_model.IntVar],
        ] = {}

        for variable in variables:
            key = (
                variable.teacher_id,
                variable.day,
            )

            variables_by_teacher_day.setdefault(
                key,
                [],
            ).append(variable.variable)

        objective_terms: list[cp_model.IntVar] = []

        for teacher in problem.teachers:
            if not teacher.is_active:
                continue

            teacher_days = {
                day
                for (
                    teacher_id,
                    day,
                ) in variables_by_teacher_day
                if teacher_id == teacher.id
            }

            if not teacher_days:
                continue

            max_daily_load = model.new_int_var(
                0,
                len(variables),
                f"teacher_{teacher.id}_max_daily_load",
            )

            for day in sorted(teacher_days):
                day_variables = variables_by_teacher_day[
                    (teacher.id, day)
                ]

                daily_load = model.new_int_var(
                    0,
                    len(day_variables),
                    f"teacher_{teacher.id}_{day}_daily_load",
                )

                model.add(
                    daily_load == sum(day_variables)
                )

                model.add(
                    max_daily_load >= daily_load
                )

            objective_terms.append(max_daily_load)

        if objective_terms:
            model.minimize(
                self.weight * sum(objective_terms)
            )


def apply_solver_objectives(
    *,
    model: cp_model.CpModel,
    problem: SchedulingProblem,
    variables: tuple[AssignmentVariable, ...],
    objective: SolverObjective | None,
) -> None:
    """
    Apply the configured solver objective to the CP-SAT model.

    A missing objective means pure feasibility solving.
    Hard constraints remain owned by SolverModelBuilder.
    """

    if objective is None:
        return

    objective.apply(
        model=model,
        problem=problem,
        variables=variables,
    )
