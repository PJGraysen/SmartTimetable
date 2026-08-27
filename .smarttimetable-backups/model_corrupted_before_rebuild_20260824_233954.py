from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.enums import PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.variables import AssignmentVariable

# ==========================================================================
# AUTHORITATIVE SIMULTANEOUS SUBJECT BLOCKS
# ==========================================================================

SIMULTANEOUS_SUBJECT_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"BIO", "MUSIC", "FRE"}),
    frozenset({"CHEM", "PHY", "LIT"}),
    frozenset({"GEO", "HIS", "COMP"}),
    frozenset({"CM", "EM"}),
)


def simultaneous_group_for_subject(
    subject_code: str | None,
) -> frozenset[str] | None:
    if not subject_code:
        return None

    normalized = subject_code.strip().upper()

    for group in SIMULTANEOUS_SUBJECT_GROUPS:
        if normalized in group:
            return group

    return None




# ============================================================
# GRADE 10 SIMULTANEOUS OPTION BLOCKS
# ============================================================

SIMULTANEOUS_OPTION_BLOCKS: tuple[frozenset[str], ...] = (
    frozenset({"AGRI", "BUS"}),
    frozenset({"BIO", "MUS", "FRE"}),
    frozenset({"CHEM", "PHY", "LIT"}),
    frozenset({"GEO", "HIST", "CS"}),
)


# ============================================================
# SOLVER MODEL
# ============================================================

@dataclass(slots=True)
class SolverModel:
    """
    CP-SAT model together with the assignment variables created for it.
    """

    model: cp_model.CpModel
    variables: tuple[AssignmentVariable, ...]

    def variables_for_lesson(
        self,
        lesson_requirement_id: UUID,
    ) -> tuple[AssignmentVariable, ...]:
        return tuple(
            variable
            for variable in self.variables
            if variable.lesson_requirement_id
            == lesson_requirement_id
        )


# ============================================================
# SOLVER MODEL BUILDER
# ============================================================

class SolverModelBuilder:
    """
    Builds the CP-SAT model from a validated SchedulingProblem.

    The domain model is authoritative:

        LessonRequirement.instructional_group_id
            ->
        AssignmentVariable.instructional_group_id

    Teacher and room assignments remain independent.

    An optional solver objective is applied after all assignment
    variables and hard constraints have been created.
    """

    def __init__(
        self,
        *,
        objective=None,
    ) -> None:
        self.objective = objective

    # ============================================================
    # BUILD
    # ============================================================

    def build(
        self,
        problem: SchedulingProblem,
    ) -> SolverModel:

        model = cp_model.CpModel()

        variables = self._create_assignment_variables(
            model=model,
            problem=problem,
        )

        self._add_lesson_requirement_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_simultaneous_subject_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_simultaneous_option_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_teacher_clash_constraints(
            model=model,
            variables=variables,
        )

        self._add_group_clash_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_room_clash_constraints(
            model=model,
            variables=variables,
        )

        self._add_teacher_availability_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_teacher_free_afternoon_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_room_availability_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        return SolverModel(
            model=model,
            variables=tuple(variables),
        )

        # --------------------------------------------------------
        # SOFT OBJECTIVE
        # --------------------------------------------------------
        # Hard constraints above remain authoritative. The optional
        # objective is applied only after every assignment variable
        # and hard constraint exists, because objective builders
        # may create auxiliary CP-SAT variables.
        if self.objective is not None:
            self.objective.apply(
                model=model,
                problem=problem,
                variables=tuple(variables),
            )


    # ============================================================
    # SUBJECT CODE NORMALIZATION
    # ============================================================

    @staticmethod
    def _normalize_subject_code(
        value,
    ) -> str:

        if value is None:
            return ""

        if isinstance(value, str):
            text = value
        else:
            text = str(value)

        text = (
            text
            .strip()
            .upper()
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
        )

        aliases = {
            "AGRICULTURE": "AGRI",
            "AGRIC": "AGRI",
            "BIOLOGY": "BIO",
            "MUSIC": "MUS",
            "FRENCH": "FRE",
            "CHEMISTRY": "CHEM",
            "PHYSICS": "PHY",
            "LITERATURE": "LIT",
            "GEOGRAPHY": "GEO",
            "HISTORY": "HIST",
            "COMPUTER": "CS",
            "COMPUTERSCIENCE": "CS",
            "COMPUTERSTUDIES": "CS",
            "BUSINESS": "BUS",
        }

        return aliases.get(
            text,
            text,
        )

    def _requirement_subject_code(
        self,
        requirement,
    ) -> str:

        candidate_attributes = (
            "subject_code",
            "subject",
            "subject_id",
        )

        for attribute in candidate_attributes:

            if not hasattr(
                requirement,
                attribute,
            ):
                continue

            value = getattr(
                requirement,
                attribute,
            )

            if value is None:
                continue

            for nested_attribute in (
                "code",
                "name",
                "subject_code",
                "subject_name",
            ):

                if not hasattr(
                    value,
                    nested_attribute,
                ):
                    continue

                nested_value = getattr(
                    value,
                    nested_attribute,
                )

                normalized = (
                    self._normalize_subject_code(
                        nested_value,
                    )
                )

                if normalized:
                    return normalized

            normalized = (
                self._normalize_subject_code(
                    value,
                )
            )

            if normalized:
                return normalized

        return ""

    # ============================================================
    # GRADE 10 IDENTIFICATION
    # ============================================================

    @staticmethod
    def _is_grade10_requirement(
        requirement,
        problem: SchedulingProblem,
    ) -> bool:

        group = next(
            (
                group
                for group in problem.instructional_groups
                if group.id
                == requirement.instructional_group_id
            ),
            None,
        )

        if group is None:
            return False

        values = (
            getattr(
                group,
                "name",
                "",
            ),
            getattr(
                group,
                "code",
                "",
            ),
            getattr(
                group,
                "display_name",
                "",
            ),
        )

        normalized = " ".join(
            str(value or "")
            .strip()
            .lower()
            for value in values
        )

        return (
            "grade 10" in normalized
            or "grade10" in normalized
            or normalized.strip() == "g10"
            or normalized.strip() == "g10a"
        )

    # ============================================================
    # SIMULTANEOUS BLOCK IDENTIFICATION
    # ============================================================

    def _requirement_block(
        self,
        requirement,
        problem: SchedulingProblem,
    ) -> frozenset[str] | None:

        if not self._is_grade10_requirement(
            requirement,
            problem,
        ):
            return None

        subject_code = (
            self._requirement_subject_code(
                requirement,
            )
        )

        if not subject_code:
            return None

        for block in SIMULTANEOUS_OPTION_BLOCKS:

            if subject_code in block:
                return block

        return None

    # ============================================================
    # ASSIGNMENT VARIABLE CREATION
    # ============================================================

    def _create_assignment_variables(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
    ) -> list[AssignmentVariable]:

        variables: list[AssignmentVariable] = []

        active_requirements = [
            requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        ]

        active_teachers = [
            teacher
            for teacher in problem.teachers
            if teacher.is_active
        ]

        active_groups = [
            group
            for group in problem.instructional_groups
            if group.is_active
        ]

        active_rooms = [
            room
            for room in problem.rooms
            if room.is_active
        ]

        teachers_by_requirement: dict[
            UUID,
            list[UUID],
        ] = defaultdict(list)

        for assignment in problem.teacher_assignments:

            if not assignment.is_active:
                continue

            teachers_by_requirement[
                assignment.lesson_requirement_id
            ].append(
                assignment.teacher_id
            )

        valid_teacher_ids = {
            teacher.id
            for teacher in active_teachers
        }

        valid_group_ids = {
            group.id
            for group in active_groups
        }

        valid_room_ids = {
            room.id
            for room in active_rooms
        }

        for requirement in active_requirements:

            instructional_group_id = (
                requirement.instructional_group_id
            )

            if instructional_group_id not in valid_group_ids:
                continue

            eligible_teacher_ids = [
                teacher_id
                for teacher_id in teachers_by_requirement[
                    requirement.id
                ]
                if teacher_id in valid_teacher_ids
            ]

            for teacher_id in eligible_teacher_ids:

                for slot in problem.slots:

                    period = problem.period_by_id.get(
                        slot.period_id
                    )

                    if period is None:
                        continue

                    if not period.is_active:
                        continue

                    if not period.is_teaching_period:
                        continue

                    for room in active_rooms:

                        if room.id not in valid_room_ids:
                            continue

                        variable_name = (
                            "assign_"
                            f"{requirement.id}_"
                            f"{teacher_id}_"
                            f"{slot.day.value}_"
                            f"{slot.period_id}_"
                            f"{room.id}"
                        )

                        variable = (
                            model.new_bool_var(
                                variable_name,
                            )
                        )

                        variables.append(
                            AssignmentVariable(
                                lesson_requirement_id=(
                                    requirement.id
                                ),
                                instructional_group_id=(
                                    instructional_group_id
                                ),
                                teacher_id=teacher_id,
                                period_id=slot.period_id,
                                day=slot.day.value,
                                room_id=room.id,
                                variable=variable,
                            )
                        )

        return variables

    # ============================================================
    # LESSON FREQUENCY
    # ============================================================

    def _add_lesson_requirement_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Enforce the authoritative weekly lesson requirement.

        Every active lesson requirement must be scheduled exactly
        periods_per_week times.

        This is a HARD constraint.
        """

        variables_by_requirement: dict[
            UUID, list[cp_model.IntVar]
        ] = defaultdict(list)

        for variable in variables:
            variables_by_requirement[
                variable.lesson_requirement_id
            ].append(variable.variable)

        for requirement in problem.lesson_requirements:

            if not requirement.is_active:
                continue

            requirement_variables = variables_by_requirement.get(
                requirement.id,
                [],
            )

            required_count = requirement.periods_per_week

            if required_count < 0:
                raise ValueError(
                    f"Lesson requirement {requirement.id} has invalid "
                    f"periods_per_week={required_count}."
                )

            if not requirement_variables:
                if required_count > 0:
                    raise ValueError(
                        f"Active lesson requirement {requirement.id} "
                        f"requires {required_count} periods but has "
                        f"no candidate assignment variables."
                    )

                continue

            model.add(
                sum(requirement_variables) == required_count
            )

    # ------------------------------------------------------------------
    # Teacher clashes
    # ------------------------------------------------------------------


        self,
        *,
        model: cp_model.CpModel,
        variables: list[AssignmentVariable],
    ) -> None:

        groups: dict[
            tuple[UUID, str, UUID],
            list[cp_model.IntVar],
        ] = defaultdict(list)

        for variable in variables:

            groups[
                (
                    variable.teacher_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(
                variable.variable
            )

        for grouped_variables in groups.values():

            model.add_at_most_one(
                grouped_variables
            )

    # ============================================================
    # INSTRUCTIONAL GROUP CLASHES
    # ============================================================

    def _add_simultaneous_subject_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Force subjects belonging to the same configured combination
        to occupy the same day and period for the same instructional group.

        Each subject retains its own teacher assignment.
        """

        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        variables_by_requirement: dict[
            UUID, list[AssignmentVariable]
        ] = defaultdict(list)

        for variable in variables:
            if variable.lesson_requirement_id in requirements_by_id:
                variables_by_requirement[
                    variable.lesson_requirement_id
                ].append(variable)

        grouped_requirements: dict[
            tuple[UUID, frozenset[str]],
            list[UUID],
        ] = defaultdict(list)

        for requirement in requirements_by_id.values():

            block = simultaneous_group_for_subject(
                requirement.subject_code
            )

            if block is None:
                continue

            grouped_requirements[
                (
                    requirement.instructional_group_id,
                    block,
                )
            ].append(requirement.id)

        for (
            instructional_group_id,
            block,
        ), requirement_ids in grouped_requirements.items():

            if len(requirement_ids) < 2:
                continue

            requirements = [
                requirements_by_id[requirement_id]
                for requirement_id in requirement_ids
            ]

            weekly_counts = {
                requirement.periods_per_week
                for requirement in requirements
            }

            if len(weekly_counts) != 1:
                raise ValueError(
                    "Simultaneous subject block has mismatched "
                    f"period counts for group "
                    f"{instructional_group_id}: "
                    f"{sorted(weekly_counts)}."
                )

            first_requirement_id = requirement_ids[0]

            first_variables = variables_by_requirement[
                first_requirement_id
            ]

            for other_requirement_id in requirement_ids[1:]:

                other_variables = variables_by_requirement[
                    other_requirement_id
                ]

                all_keys = {
                    (variable.day, variable.period_id)
                    for variable in first_variables
                } | {
                    (variable.day, variable.period_id)
                    for variable in other_variables
                }

                for day, period_id in all_keys:

                    first_slot = [
                        variable.variable
                        for variable in first_variables
                        if (
                            variable.day == day
                            and variable.period_id == period_id
                        )
                    ]

                    other_slot = [
                        variable.variable
                        for variable in other_variables
                        if (
                            variable.day == day
                            and variable.period_id == period_id
                        )
                    ]

                    model.add(
                        sum(first_slot) == sum(other_slot)
                    )

    def _add_group_clash_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Prevent unrelated subjects from occupying the same
        instructional-group slot.

        Explicit simultaneous subject combinations are allowed
        to share the same group/day/period.
        """

        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
        }

        groups: dict[
            tuple[UUID, str, UUID],
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            groups[
                (
                    variable.teaching_group_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(variable)

        for grouped_variables in groups.values():

            by_block: dict[
                frozenset[str] | None,
                list[cp_model.IntVar],
            ] = defaultdict(list)

            for variable in grouped_variables:

                requirement = requirements_by_id.get(
                    variable.lesson_requirement_id
                )

                subject_code = (
                    requirement.subject_code
                    if requirement is not None
                    else None
                )

                block = simultaneous_group_for_subject(
                    subject_code
                )

                by_block[block].append(
                    variable.variable
                )

            ordinary = by_block.get(None, [])

            model.add_at_most_one(ordinary)

            blocks = [
                block
                for block in by_block
                if block is not None
            ]

            for block in blocks:

                block_variables = by_block[block]

                for ordinary_variable in ordinary:
                    model.add_at_most_one(
                        [
                            ordinary_variable,
                            *block_variables,
                        ]
                    )

            for index, first_block in enumerate(blocks):

                for second_block in blocks[index + 1:]:

                    model.add_at_most_one(
                        [
                            *by_block[first_block],
                            *by_block[second_block],
                        ]
                    )

    def _add_room_clash_constraints(
        self,
        *,
        model: cp_model.CpModel,
        variables: list[AssignmentVariable],
    ) -> None:

        groups: dict[
            tuple[UUID, str, UUID],
            list[cp_model.IntVar],
        ] = defaultdict(list)

        for variable in variables:

            if variable.room_id is None:
                continue

            groups[
                (
                    variable.room_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(
                variable.variable
            )

        for grouped_variables in groups.values():

            model.add_at_most_one(
                grouped_variables
            )

    # ============================================================
    # TEACHER AVAILABILITY
    # ============================================================

    def _add_teacher_availability_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        unavailable_slots: set[
            tuple[UUID, str, UUID]
        ] = {
            (
                availability.teacher_id,
                availability.day.value,
                availability.period_id,
            )
            for availability in problem.teacher_availability
            if availability.is_active
            and not availability.is_available
        }

        for variable in variables:

            key = (
                variable.teacher_id,
                variable.day,
                variable.period_id,
            )

            if key in unavailable_slots:

                model.add(
                    variable.variable == 0
                )

    # ============================================================
    # MANDATORY TEACHER FREE AFTERNOON
    # ============================================================

    def _add_teacher_free_afternoon_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        for teacher in problem.teachers:

            if not teacher.is_active:
                continue

            free_afternoon = (
                problem.teacher_free_afternoon(
                    teacher.id
                )
            )

            if free_afternoon is None:

                raise ValueError(
                    f"Teacher {teacher.id} has no "
                    "free-afternoon assignment."
                )

            for variable in variables:

                if variable.teacher_id != teacher.id:
                    continue

                if (
                    variable.day
                    != free_afternoon.day.value
                ):
                    continue

                period = problem.period_by_id.get(
                    variable.period_id
                )

                if period is None:
                    continue

                if not period.is_active:
                    continue

                if not period.is_teaching_period:
                    continue

                if (
                    period.part_of_day
                    != PartOfDay.AFTERNOON
                ):
                    continue

                model.add(
                    variable.variable == 0
                )

    # ============================================================
    # ROOM AVAILABILITY
    # ============================================================

    def _add_room_availability_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        unavailable_slots: set[
            tuple[UUID, str, UUID]
        ] = {
            (
                availability.room_id,
                availability.day.value,
                availability.period_id,
            )
            for availability in problem.room_availability
            if availability.is_active
            and not availability.is_available
        }

        for variable in variables:

            if variable.room_id is None:
                continue

            key = (
                variable.room_id,
                variable.day,
                variable.period_id,
            )

            if key in unavailable_slots:

                model.add(
                    variable.variable == 0
                )
