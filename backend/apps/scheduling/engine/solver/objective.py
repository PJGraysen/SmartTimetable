from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.variables import AssignmentVariable


def _is_empty_objective_expression(expression: object) -> bool:
    """
    Determine whether an objective expression is empty.

    Empty objective builders in this module return the integer 0.

    CP-SAT expressions are not compared directly with zero because
    LinearExpr / IntVar comparisons can produce constraint expressions
    rather than a normal Python boolean.

    Therefore this helper deliberately checks only plain scalar values.
    """
    if expression is None:
        return True

    if isinstance(expression, (int, float)):
        return expression == 0

    return False


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

    1. Teacher workload balancing.
    2. Lesson distribution across days.
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

    def build_expression(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> object:
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
            return 0

        return sum(weighted_terms)

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        expression = self.build_expression(
            model=model,
            problem=problem,
            variables=variables,
        )

        if _is_empty_objective_expression(expression):
            return

        model.minimize(expression)

    def _teacher_workload_terms(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> list[cp_model.IntVar]:
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
                    for teacher_id, day in variables_by_teacher_day
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

    def _lesson_distribution_terms(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> list[cp_model.IntVar]:
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
                    for requirement_id, day
                    in variables_by_requirement_day
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
    Soft objective penalizing a teacher being scheduled in consecutive
    teaching periods on the same day.

    Consecutive assignments are represented by Boolean penalty variables.

    A penalty variable is 1 exactly when:

        first_period_assignment == 1
        AND
        second_period_assignment == 1

    The objective minimizes the weighted sum of those penalty variables.
    """

    weight: int = 1

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                "Teacher consecutive-period objective weight must be "
                "greater than zero."
            )

    def build_expression(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> object:
        penalty_terms = self._consecutive_period_terms(
            model=model,
            problem=problem,
            variables=variables,
        )

        if not penalty_terms:
            return 0

        return self.weight * sum(penalty_terms)

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        expression = self.build_expression(
            model=model,
            problem=problem,
            variables=variables,
        )

        if _is_empty_objective_expression(expression):
            return

        model.minimize(expression)

    def _consecutive_period_terms(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> list[cp_model.IntVar]:
        period_by_id = problem.period_by_id

        variables_by_teacher_day_period: dict[
            tuple[UUID, str, UUID],
            list[cp_model.IntVar],
        ] = {}

        for assignment in variables:
            period = period_by_id.get(
                assignment.period_id
            )

            if period is None:
                continue

            if not period.is_active:
                continue

            if not period.is_teaching_period:
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
        ), period_variables in (
            variables_by_teacher_day_period.items()
        ):
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

            for index in range(
                len(period_numbers) - 1
            ):
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
                            >= first_variable
                            + second_variable
                            - 1
                        )

                        penalty_terms.append(
                            penalty
                        )

        return penalty_terms


# --------------------------------------------------------------------------
# Complex-subject adjacency (Soft)
# --------------------------------------------------------------------------
SCIENCE_CODES = frozenset({"BIO", "CHEM", "PHY"})
PRACTICAL_CODES = frozenset({"BIOPRAC", "CHEMPRAC", "PHYPRAC"})
MATHS_CODES = frozenset({"MAT"})
COMPLEX_CODES = SCIENCE_CODES | MATHS_CODES


@dataclass(slots=True)
class ComplexSubjectAdjacencyObjective:
    """
    Soft objective penalizing two COMPLEX subjects scheduled in
    consecutive periods on the same day for the same instructional group.

    A "complex" subject is any of the pure sciences (BIO, CHEM, PHY) or
    maths (MAT). Practicals (BIOPRAC, CHEMPRAC, PHYPRAC) are excluded by
    design so that the existing practical block rule is not disturbed.

    Rule:
        period N and period N+1 are adjacent.
        If both carry a complex subject AND the two subject codes differ,
        add a penalty.
        Same-code adjacency (e.g. a double BIO lesson) is allowed.
    """

    weight: int = 40

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                "Complex-subject adjacency weight must be greater than zero."
            )

    def build_expression(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> object:
        penalty_terms = self._adjacency_terms(
            model=model,
            problem=problem,
            variables=variables,
        )
        if not penalty_terms:
            return 0
        return self.weight * sum(penalty_terms)

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        expression = self.build_expression(
            model=model,
            problem=problem,
            variables=variables,
        )
        if _is_empty_objective_expression(expression):
            return
        model.minimize(expression)

    def _adjacency_terms(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> list[cp_model.IntVar]:
        subject_by_lr: dict[str, str] = {}
        for lr in getattr(problem, "lesson_requirements", ()) or ():
            lr_id = getattr(lr, "id", None)
            code = (
                getattr(lr, "subject_code", None)
                or getattr(getattr(lr, "subject", None), "code", None)
            )
            if lr_id is not None and code:
                subject_by_lr[str(lr_id)] = str(code).upper()

        period_by_id = problem.period_by_id
        indexed: dict[tuple[str, str], dict[int, list[tuple[str, cp_model.IntVar]]]] = {}

        for a in variables:
            period = period_by_id.get(a.period_id)
            if period is None or not period.is_active or not period.is_teaching_period:
                continue
            lr_id = (
                getattr(a, "lesson_requirement_id", None)
                or getattr(a, "requirement_id", None)
            )
            code = subject_by_lr.get(str(lr_id), "") if lr_id else ""
            if not code:
                continue
            ig_id = str(getattr(a, "instructional_group_id", ""))
            indexed.setdefault((ig_id, a.day), {}).setdefault(
                period.number, []
            ).append((code, a.variable))

        penalty_terms: list[cp_model.IntVar] = []

        for (ig_id, day), periods in indexed.items():
            nums = sorted(periods)
            for i in range(len(nums) - 1):
                n1 = nums[i]
                n2 = nums[i + 1]
                if n2 != n1 + 1:
                    continue
                for c1, v1 in periods[n1]:
                    if c1 not in COMPLEX_CODES:
                        continue
                    for c2, v2 in periods[n2]:
                        if c2 not in COMPLEX_CODES:
                            continue
                        if c1 == c2:
                            continue
                        penalty = model.new_bool_var(
                            "complex_adjacency_"
                            f"{ig_id}_{day}_{n1}_{n2}_{len(penalty_terms)}"
                        )
                        model.add(penalty <= v1)
                        model.add(penalty <= v2)
                        model.add(penalty >= v1 + v2 - 1)
                        penalty_terms.append(penalty)

        return penalty_terms


# --------------------------------------------------------------------------
# Maths morning preference (Soft)
# --------------------------------------------------------------------------
MATHS_EARLY_CUTOFF_PERIOD = 4


@dataclass(slots=True)
class MathsMorningPreferenceObjective:
    """
    Soft objective penalizing maths (MAT) scheduled after period 4
    (i.e. after the mid-morning break).

    Lower weight than the adjacency objective, because morning placement
    is a preference, not a rule.
    """

    weight: int = 12
    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                "Maths morning preference weight must be greater than zero."
            )

    def build_expression(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> object:
        penalty_terms = self._afternoon_maths_terms(
            model=model,
            problem=problem,
            variables=variables,
        )
        if not penalty_terms:
            return 0
        return self.weight * sum(penalty_terms)

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        expression = self.build_expression(
            model=model,
            problem=problem,
            variables=variables,
        )
        if _is_empty_objective_expression(expression):
            return
        model.minimize(expression)

    def _afternoon_maths_terms(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> list[cp_model.IntVar]:
        subject_by_lr: dict[str, str] = {}
        for lr in getattr(problem, "lesson_requirements", ()) or ():
            lr_id = getattr(lr, "id", None)
            code = (
                getattr(lr, "subject_code", None)
                or getattr(getattr(lr, "subject", None), "code", None)
            )
            if lr_id is not None and code:
                subject_by_lr[str(lr_id)] = str(code).upper()

        period_by_id = problem.period_by_id
        penalty_terms: list[cp_model.IntVar] = []

        for a in variables:
            period = period_by_id.get(a.period_id)
            if period is None or not period.is_active or not period.is_teaching_period:
                continue
            if period.number <= MATHS_EARLY_CUTOFF_PERIOD:
                continue
            lr_id = (
                getattr(a, "lesson_requirement_id", None)
                or getattr(a, "requirement_id", None)
            )
            code = subject_by_lr.get(str(lr_id), "") if lr_id else ""
            if code not in MATHS_CODES:
                continue
            penalty_terms.append(a.variable)

        return penalty_terms


@dataclass(slots=True)
class TeacherGapMinimizationObjective:
    """
    Soft objective penalizing idle teaching periods between a teacher's
    lessons on the same day.

    A "gap" is an empty teaching period sandwiched between two periods
    where the teacher IS assigned. Longer gaps cost proportionally more.

    Implementation:
      * Group assignment variables by (teacher, day, period_number).
      * For each (teacher, day), compute the OR of variables at each
        period ? `used[p]` boolean.
      * For each pair of periods (p_a, p_b) in the teacher's possible
        period list where p_b > p_a + 1, penalize
            (p_b - p_a - 1) * (used[p_a] AND used[p_b])
        The multiplier is realized by appending the same penalty var
        multiple times to the sum expression.
    """

    weight: int = 1

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                "Teacher gap-minimization objective weight must be "
                "greater than zero."
            )

    def build_expression(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> object:
        penalty_terms = self._gap_terms(
            model=model,
            problem=problem,
            variables=variables,
        )

        if not penalty_terms:
            return 0

        return self.weight * sum(penalty_terms)

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        expression = self.build_expression(
            model=model,
            problem=problem,
            variables=variables,
        )

        if _is_empty_objective_expression(expression):
            return

        model.minimize(expression)

    def _gap_terms(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> list[cp_model.IntVar]:
        period_by_id = problem.period_by_id

        # teacher_id -> day -> period_number -> [vars]
        by_teacher_day: dict[
            tuple[UUID, str],
            dict[int, list[cp_model.IntVar]],
        ] = {}

        for assignment in variables:
            period = period_by_id.get(assignment.period_id)
            if period is None:
                continue
            if not period.is_active or not period.is_teaching_period:
                continue

            key = (assignment.teacher_id, assignment.day)
            by_teacher_day.setdefault(key, {}).setdefault(
                period.number, []
            ).append(assignment.variable)

        penalty_terms: list[cp_model.IntVar] = []

        for (teacher_id, day), periods in by_teacher_day.items():
            period_numbers = sorted(periods)
            if len(period_numbers) < 3:
                continue

            # used[p] = OR(variables at period p)
            used: dict[int, cp_model.IntVar] = {}
            for pnum, vars_here in periods.items():
                if len(vars_here) == 1:
                    used[pnum] = vars_here[0]
                else:
                    u = model.new_bool_var(
                        f"gap_used_{teacher_id}_{day}_{pnum}_{len(penalty_terms)}"
                    )
                    model.add_max_equality(u, vars_here)
                    used[pnum] = u

            # For every non-adjacent pair, penalize (p_b - p_a - 1) *
            # (used[p_a] AND used[p_b])
            for i in range(len(period_numbers) - 1):
                p_a = period_numbers[i]
                for j in range(i + 1, len(period_numbers)):
                    p_b = period_numbers[j]
                    gap_size = p_b - p_a - 1
                    if gap_size <= 0:
                        continue

                    penalty = model.new_bool_var(
                        f"gap_{teacher_id}_{day}_{p_a}_{p_b}_{len(penalty_terms)}"
                    )
                    model.add(penalty <= used[p_a])
                    model.add(penalty <= used[p_b])
                    model.add(
                        penalty >= used[p_a] + used[p_b] - 1
                    )
                    # Weight by gap length
                    for _ in range(gap_size):
                        penalty_terms.append(penalty)

        return penalty_terms


@dataclass(slots=True)
class CompositeSolverObjective:
    """
    Combines multiple soft objectives into one CP-SAT objective.

    CP-SAT has one objective expression, so individual objective
    expressions are aggregated before model.minimize() is called.
    """

    objectives: tuple[object, ...]

    def __init__(
        self,
        objectives: tuple[object, ...] | list[object],
    ) -> None:
        self.objectives = tuple(objectives)

        for objective in self.objectives:
            if not hasattr(objective, "build_expression"):
                raise TypeError(
                    "CompositeSolverObjective requires objectives "
                    "that implement build_expression()."
                )

    def build_expression(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> object:
        expressions: list[object] = []

        for objective in self.objectives:
            expression = objective.build_expression(
                model=model,
                problem=problem,
                variables=variables,
            )

            if not _is_empty_objective_expression(expression):
                expressions.append(expression)

        if not expressions:
            return 0

        return sum(expressions)

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        expression = self.build_expression(
            model=model,
            problem=problem,
            variables=variables,
        )

        if _is_empty_objective_expression(expression):
            return

        model.minimize(expression)


# --------------------------------------------------------------------------
# Scoped stay-put penalty (Soft)
# --------------------------------------------------------------------------
@dataclass(slots=True)
class ScopedStayPutObjective:
    """
    Soft: penalize moving out-of-scope entries away from their current
    (day, period) slot during a scoped regeneration.

    ``problem.hint_assignments`` carries exactly the out-of-scope
    entries (see compute_hints_for_scope). Each hinted entry that
    deviates from its hint contributes ``1 - variable`` to the
    objective. In-scope entries are not present in the hint set and
    therefore unpenalized: the solver is free to re-arrange them.

    Master scope carries ``()`` -> this objective is a no-op and the
    model behaves identically to an unscoped run.
    """

    weight: int = 1000

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                "Scoped stay-put weight must be greater than zero."
            )

    def build_expression(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> object:
        hints = getattr(problem, "hint_assignments", ()) or ()
        if not hints:
            return 0

        hint_keys: set[tuple[str, str, str]] = set()
        for lr_id, day, period_id in hints:
            hint_keys.add((
                str(lr_id),
                str(day).strip().upper(),
                str(period_id),
            ))

        penalty_terms: list = []
        for a in variables:
            key = (
                str(a.lesson_requirement_id),
                str(a.day).strip().upper(),
                str(a.period_id),
            )
            if key in hint_keys:
                penalty_terms.append(1 - a.variable)

        if not penalty_terms:
            return 0
        return self.weight * sum(penalty_terms)

    def apply(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> None:
        expression = self.build_expression(
            model=model, problem=problem, variables=variables,
        )
        if _is_empty_objective_expression(expression):
            return
        model.minimize(expression)


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

# --------------------------------------------------------------------------
# Teacher max consecutive (Soft)
# --------------------------------------------------------------------------
@dataclass(slots=True)
class TeacherMaxConsecutiveObjective:
    """
    Soft: no teacher should teach more than 2 consecutive periods on
    the same day.

    A "consecutive" run of teaching periods is determined by raw
    period numbers: P4 -> P6 is not consecutive (P5 is a break), but
    P1 -> P2 -> P3 -> P4 is.

    For every (teacher, day, run) and every triple of adjacent
    positions in that run, a Boolean penalty is set when the teacher
    is assigned all three periods. The sum of penalties is minimized
    under the composite objective.
    """

    weight: int = 30

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                "Teacher max-consecutive weight must be greater than zero."
            )

    def build_expression(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> object:
        teaching = sorted(
            (
                p
                for p in problem.periods
                if getattr(p, "is_active", False)
                and getattr(p, "is_teaching_period", False)
            ),
            key=lambda p: int(getattr(p, "number", 0) or 0),
        )

        run_by_period: dict = {}
        pos_by_period: dict = {}
        prev_num = None
        run_idx = -1
        pos_in_run = 0
        for p in teaching:
            n = int(getattr(p, "number", 0) or 0)
            if prev_num is None or n != prev_num + 1:
                run_idx += 1
                pos_in_run = 0
            else:
                pos_in_run += 1
            run_by_period[p.id] = run_idx
            pos_by_period[p.id] = pos_in_run
            prev_num = n

        buckets: dict = {}
        for v in variables:
            if v.teacher_id is None:
                continue
            run_id = run_by_period.get(v.period_id)
            if run_id is None:
                continue
            pos = pos_by_period[v.period_id]
            key = (v.teacher_id, v.day, run_id)
            buckets.setdefault(key, {}).setdefault(pos, []).append(
                v.variable
            )

        penalty_terms: list = []
        idx = 0

        for (teacher_id, day, run_id), by_pos in buckets.items():

            # presence[p] = 1 iff the teacher has ANY assignment at
            # that position on that day. This handles synchronized
            # teacher events correctly: whether one or two LRs place
            # the teacher at the position, presence is 1.
            presence: dict = {}
            for p, var_list in by_pos.items():
                present = model.new_bool_var(
                    f"maxcons_presence_{idx}"
                )
                # present >= each var  (present is 1 if any is 1)
                for v in var_list:
                    model.add(present >= v)
                # present <= sum(var_list)  (present must be 0 if all 0)
                model.add(present <= sum(var_list))
                presence[p] = present
                idx += 1

            positions = sorted(presence.keys())
            pos_set = set(positions)
            for p in positions:
                if p + 1 in pos_set and p + 2 in pos_set:
                    triple = (
                        presence[p]
                        + presence[p + 1]
                        + presence[p + 2]
                    )
                    violation = model.new_bool_var(
                        f"maxcons_viol_{idx}"
                    )
                    # violation = 1 whenever all three positions are
                    # occupied by the teacher. If any is 0, violation
                    # is free; the solver will pick 0 to avoid penalty.
                    model.add(violation >= triple - 2)
                    penalty_terms.append(violation)
                    idx += 1

        if not penalty_terms:
            return 0

        return sum(penalty_terms) * self.weight

# --------------------------------------------------------------------------
# Teacher daily-load balance (Soft)
# --------------------------------------------------------------------------
@dataclass(slots=True)
class TeacherDailyLoadObjective:
    """
    Soft: penalize heavy teaching days.

    For every (teacher, day), compute the teacher's physical presence
    at each teaching position (deduped so synchronized E/W events
    count once). If the total exceeds ``threshold``, apply a
    quadratic penalty (excess squared, linearized via auxiliary
    booleans) scaled by ``weight``.

    Because the penalty is soft, no model can go INFEASIBLE from this
    objective alone. It only nudges the solver to spread heavy
    teachers' periods more evenly across the week.
    """

    threshold: int = 6
    weight: int = 8
    max_excess: int = 4

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise ValueError("threshold must be >= 1")
        if self.weight <= 0:
            raise ValueError("weight must be > 0")
        if self.max_excess < 1:
            raise ValueError("max_excess must be >= 1")

    def build_expression(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: tuple[AssignmentVariable, ...],
    ) -> object:
        # Group variables by (teacher, day) and (teacher, day, position).
        by_teacher_day_pos: dict = {}
        for v in variables:
            if v.teacher_id is None:
                continue
            period = problem.period_by_id.get(v.period_id)
            if period is None:
                continue
            if not getattr(period, "is_teaching_period", False):
                continue
            try:
                pnum = int(getattr(period, "number", 0) or 0)
            except (TypeError, ValueError):
                continue
            key = (v.teacher_id, v.day)
            by_teacher_day_pos.setdefault(key, {}).setdefault(
                pnum, []
            ).append(v.variable)

        penalty_terms: list = []
        idx = 0
        for (teacher_id, day), by_pos in by_teacher_day_pos.items():
            # Presence per position: OR over all vars there.
            presence: list = []
            for pnum, var_list in by_pos.items():
                present = model.new_bool_var(
                    f"dayload_presence_{idx}"
                )
                for vv in var_list:
                    model.add(present >= vv)
                model.add(present <= sum(var_list))
                presence.append(present)
                idx += 1

            total = sum(presence)
            # Linearize (total - threshold)^2 up to max_excess.
            # over_k = 1 iff total >= threshold + k
            # penalty = sum_{k=1}^{K} (2k-1) * over_k  == max(0, excess)^2
            for k in range(1, self.max_excess + 1):
                over_k = model.new_bool_var(f"dayload_over_{idx}")
                # over_k = 1 -> total >= threshold + k.
                # over_k = 0 -> trivially satisfied (0 >= 0).
                # Form: total >= (threshold + k) * over_k.
                model.add(
                    total >= (self.threshold + k) * over_k
                )
                # If total < threshold + k, then over_k = 0 (implied
                # by the above since forcing over_k = 1 would violate).
                # The solver will pick over_k = 0 when possible
                # because over_k has positive weight below.
                penalty_terms.append((2 * k - 1) * over_k)
                idx += 1

        if not penalty_terms:
            return 0

        return sum(penalty_terms) * self.weight

