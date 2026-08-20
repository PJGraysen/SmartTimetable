from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.variables import AssignmentVariable


@dataclass(frozen=True, slots=True)
class ObjectiveTerm:
    """
    One weighted optimization term.

    Positive weights represent penalties because CP-SAT minimizes
    the objective expression.
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
    Soft optimization objective for teacher workload and lesson
    distribution.

    The objective has two components:

    1. Teacher workload balancing:
       Minimize the maximum number of lessons assigned to each teacher
       on any single day.

    2. Lesson distribution:
       Minimize the maximum number of lessons belonging to the same
       lesson requirement on any single day.

    Both components are soft objectives. They can improve timetable
    quality but can never override hard scheduling constraints.
    """

    weight: int = 1
    lesson_distribution_weight: int = 1

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                "Teacher workload objective weight must be greater "
                "than zero."
            )

        if self.lesson_distribution_weight <= 0:
            raise ValueError(
                "Lesson distribution objective weight must be greater "
                "than zero."
            )

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        teacher_terms = self._teacher_workload_terms(
            model=model,
            problem=problem,
            variables=variables,
        )

        lesson_distribution_terms = (
            self._lesson_distribution_terms(
                model=model,
                problem=problem,
                variables=variables,
            )
        )

        objective_terms: list[cp_model.IntVar] = []

        objective_terms.extend(teacher_terms)
        objective_terms.extend(lesson_distribution_terms)

        if not objective_terms:
            return

        weighted_terms: list[object] = []

        if teacher_terms:
            weighted_terms.append(
                self.weight * sum(teacher_terms)
            )

        if lesson_distribution_terms:
            weighted_terms.append(
                self.lesson_distribution_weight
                * sum(lesson_distribution_terms)
            )

        if not weighted_terms:
            return

        model.minimize(sum(weighted_terms))

    # ------------------------------------------------------------------
    # Teacher workload
    # ------------------------------------------------------------------

    def _teacher_workload_terms(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> list[cp_model.IntVar]:
        """
        Create one maximum-daily-workload variable for every active
        teacher represented by solver variables.
        """

        variables_by_teacher_day: dict[
            tuple[UUID, str],
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

            teacher_days = sorted(
                {
                    day
                    for (
                        teacher_id,
                        day,
                    ) in variables_by_teacher_day
                    if teacher_id == teacher.id
                }
            )

            if not teacher_days:
                continue

            max_daily_load = model.new_int_var(
                0,
                len(variables),
                f"teacher_{teacher.id}_max_daily_load",
            )

            for day in teacher_days:
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

        return objective_terms

    # ------------------------------------------------------------------
    # Lesson distribution
    # ------------------------------------------------------------------

    def _lesson_distribution_terms(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> list[cp_model.IntVar]:
        """
        Create one maximum-daily-load variable for every active lesson
        requirement represented by solver variables.

        This encourages lessons belonging to the same requirement to be
        distributed across different days whenever the hard constraints
        permit it.
        """

        variables_by_requirement_day: dict[
            tuple[UUID, str],
            list[cp_model.IntVar],
        ] = {}

        for variable in variables:
            key = (
                variable.lesson_requirement_id,
                variable.day,
            )

            variables_by_requirement_day.setdefault(
                key,
                [],
            ).append(variable.variable)

        objective_terms: list[cp_model.IntVar] = []

        for requirement in problem.lesson_requirements:
            if not requirement.is_active:
                continue

            requirement_days = sorted(
                {
                    day
                    for (
                        requirement_id,
                        day,
                    ) in variables_by_requirement_day
                    if requirement_id == requirement.id
                }
            )

            if not requirement_days:
                continue

            max_daily_load = model.new_int_var(
                0,
                max(
                    1,
                    requirement.periods_per_week,
                ),
                (
                    "requirement_"
                    f"{requirement.id}_max_daily_load"
                ),
            )

            for day in requirement_days:
                day_variables = variables_by_requirement_day[
                    (requirement.id, day)
                ]

                daily_load = model.new_int_var(
                    0,
                    len(day_variables),
                    (
                        "requirement_"
                        f"{requirement.id}_{day}_daily_load"
                    ),
                )

                model.add(
                    daily_load == sum(day_variables)
                )

                model.add(
                    max_daily_load >= daily_load
                )

            objective_terms.append(max_daily_load)

        return objective_terms


@dataclass(slots=True)
class TeacherConsecutivePeriodObjective:
    """
    Soft optimization objective that penalizes a teacher being scheduled
    in consecutive teaching periods on the same day.

    A penalty variable is created for every pair of candidate assignments
    belonging to the same teacher, same day and consecutive timetable
    periods.

    The penalty variable is one exactly when both assignments are selected.

    This is deliberately a soft objective. It never makes a timetable
    infeasible merely because consecutive teaching periods are unavoidable.
    """

    weight: int = 1

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                "Teacher consecutive-period objective weight must be "
                "greater than zero."
            )

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        penalty_terms = self._consecutive_period_terms(
            model=model,
            problem=problem,
            variables=variables,
        )

        if not penalty_terms:
            return

        model.minimize(
            self.weight * sum(penalty_terms)
        )

    def _consecutive_period_terms(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> list[cp_model.IntVar]:
        """
        Create penalty variables for consecutive teacher assignments.

        Period adjacency is determined from the domain PeriodEntity.number,
        rather than from the order in which AssignmentVariable instances
        happen to appear.
        """

        period_by_id = problem.period_by_id

        variables_by_teacher_day_period: dict[
            tuple[UUID, str, UUID],
            list[cp_model.IntVar],
        ] = {}

        for assignment in variables:
            period = period_by_id.get(assignment.period_id)

            if period is None:
                continue

            if not period.is_active or not period.is_teaching_period:
                continue

            key = (
                assignment.teacher_id,
                assignment.day,
                assignment.period_id,
            )

            variables_by_teacher_day_period.setdefault(
                key,
                [],
            ).append(assignment.variable)

        indexed_variables: dict[
            tuple[UUID, str],
            dict[int, list[cp_model.IntVar]],
        ] = {}

        for (
            teacher_id,
            day,
            period_id,
        ), period_variables in variables_by_teacher_day_period.items():
            period = period_by_id[period_id]

            indexed_variables.setdefault(
                (teacher_id, day),
                {},
            ).setdefault(
                period.number,
                [],
            ).extend(period_variables)

        penalty_terms: list[cp_model.IntVar] = []

        for (
            teacher_id,
            day,
        ), periods in indexed_variables.items():
            period_numbers = sorted(periods)

            for index in range(len(period_numbers) - 1):
                first_number = period_numbers[index]
                second_number = period_numbers[index + 1]

                if second_number != first_number + 1:
                    continue

                first_variables = periods[first_number]
                second_variables = periods[second_number]

                for first_variable in first_variables:
                    for second_variable in second_variables:
                        penalty = model.new_bool_var(
                            (
                                "teacher_consecutive_"
                                f"{teacher_id}_{day}_"
                                f"{first_number}_{second_number}_"
                                f"{len(penalty_terms)}"
                            )
                        )

                        model.add(
                            penalty <= first_variable
                        )
                        model.add(
                            penalty <= second_variable
                        )
                        model.add(
                            penalty
                            >= first_variable + second_variable - 1
                        )

                        penalty_terms.append(penalty)

        return penalty_terms


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
