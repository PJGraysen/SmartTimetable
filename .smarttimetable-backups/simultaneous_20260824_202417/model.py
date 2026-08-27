from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.enums import PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.objective import apply_solver_objectives
from apps.scheduling.engine.solver.variables import AssignmentVariable


# ---------------------------------------------------------------------------
# AUTHORITATIVE GRADE 10 SIMULTANEOUS OPTION BLOCKS
# ---------------------------------------------------------------------------

SIMULTANEOUS_OPTION_BLOCKS = (
    frozenset({"AGRI", "BUS"}),
    frozenset({"BIO", "MUS", "FRE"}),
    frozenset({"CHEM", "PHY", "LIT"}),
    frozenset({"GEO", "HIST", "CS"}),
)


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
            if variable.lesson_requirement_id == lesson_requirement_id
        )


class SolverModelBuilder:
    """
    Builds the complete CP-SAT timetable model.

    Hard constraints are applied first.
    Optional optimization objectives are applied last.
    """

    def __init__(
        self,
        *,
        objective=None,
    ) -> None:
        self.objective = objective

    # ------------------------------------------------------------------
    # BUILD
    # ------------------------------------------------------------------

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

        self._add_lesson_requirement_slot_constraints(
            model=model,
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

        self._add_simultaneous_option_constraints(
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

        if self.objective is not None:
            apply_solver_objectives(
                model=model,
                problem=problem,
                variables=tuple(variables),
                objective=self.objective,
            )

        return SolverModel(
            model=model,
            variables=tuple(variables),
        )

    # ------------------------------------------------------------------
    # VARIABLE CREATION
    # ------------------------------------------------------------------

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

        valid_group_ids = {
            group.id
            for group in active_groups
        }

        valid_teacher_ids = {
            teacher.id
            for teacher in active_teachers
        }

        valid_room_ids = {
            room.id
            for room in active_rooms
        }

        teaching_period_ids = {
            period.id
            for period in problem.teaching_periods
        }

        for requirement in active_requirements:

            if requirement.instructional_group_id not in valid_group_ids:
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

                    if slot.period_id not in teaching_period_ids:
                        continue

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

                        name = (
                            f"assign_"
                            f"{requirement.id}_"
                            f"{teacher_id}_"
                            f"{slot.day.value}_"
                            f"{slot.period_id}_"
                            f"{room.id}"
                        )

                        variable = model.new_bool_var(name)

                        variables.append(
                            AssignmentVariable(
                                lesson_requirement_id=requirement.id,
                                teacher_id=teacher_id,
                                instructional_group_id=(
                                    requirement.instructional_group_id
                                ),
                                period_id=slot.period_id,
                                day=slot.day.value,
                                room_id=room.id,
                                variable=variable,
                            )
                        )

        return variables

    # ------------------------------------------------------------------
    # SUBJECT IDENTIFICATION
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_subject_code(
        value: object,
    ) -> str:

        if value is None:
            return ""

        text = str(value).strip().upper()

        if not text:
            return ""

        replacements = {
            "AGRICULTURE": "AGRI",
            "AGRIC": "AGRI",
            "AGRI": "AGRI",

            "BUSINESS": "BUS",
            "BUSINESS STUDIES": "BUS",
            "BUSINESS STUDY": "BUS",
            "BUS": "BUS",

            "BIOLOGY": "BIO",
            "BIO": "BIO",

            "MUSIC": "MUS",
            "MUS": "MUS",

            "FRENCH": "FRE",
            "FRE": "FRE",

            "CHEMISTRY": "CHEM",
            "CHEM": "CHEM",

            "PHYSICS": "PHY",
            "PHY": "PHY",

            "LITERATURE": "LIT",
            "LIT": "LIT",

            "GEOGRAPHY": "GEO",
            "GEO": "GEO",

            "HISTORY": "HIST",
            "HISTORIES": "HIST",
            "HIST": "HIST",

            "COMPUTER SCIENCE": "CS",
            "COMPUTER STUDIES": "CS",
            "COMPUTER STUDY": "CS",
            "COMPUTER": "CS",
            "CS": "CS",

            "ENGLISH": "ENG",
            "ENG": "ENG",

            "KISWAHILI": "KIS",
            "KIS": "KIS",

            "ICT": "ICT",
        }

        return replacements.get(text, text)

    def _requirement_subject_code(
        self,
        requirement,
    ) -> str:
        """
        Resolve the subject identity without assuming one specific version
        of the domain entity.

        We deliberately inspect the common subject/code/name representations.
        """

        candidate_attributes = (
            "subject_code",
            "code",
            "subject",
            "subject_name",
            "name",
            "lesson_requirement_name",
            "title",
            "description",
        )

        for attribute in candidate_attributes:

            if not hasattr(requirement, attribute):
                continue

            value = getattr(
                requirement,
                attribute,
            )

            if value is None:
                continue

            # Nested subject entity.
            for nested_attribute in (
                "code",
                "name",
                "subject_code",
                "subject_name",
            ):

                if hasattr(value, nested_attribute):

                    nested_value = getattr(
                        value,
                        nested_attribute,
                    )

                    normalized = (
                        self._normalize_subject_code(
                            nested_value
                        )
                    )

                    if normalized:
                        return normalized

            normalized = self._normalize_subject_code(
                value
            )

            if normalized:
                return normalized

        return ""

    # ------------------------------------------------------------------
    # GRADE 10 IDENTIFICATION
    # ------------------------------------------------------------------

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
            getattr(group, "name", ""),
            getattr(group, "code", ""),
            getattr(group, "display_name", ""),
        )

        normalized = " ".join(
            str(value or "").strip().lower()
            for value in values
        )

        return (
            "grade 10" in normalized
            or "grade10" in normalized
            or normalized.strip() == "g10"
            or normalized.strip() == "g10a"
        )

    # ------------------------------------------------------------------
    # BLOCK IDENTIFICATION
    # ------------------------------------------------------------------

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

        subject_code = self._requirement_subject_code(
            requirement
        )

        if not subject_code:
            return None

        for block in SIMULTANEOUS_OPTION_BLOCKS:

            if subject_code in block:
                return block

        return None

    # ------------------------------------------------------------------
    # LESSON FREQUENCY
    # ------------------------------------------------------------------

    def _add_lesson_requirement_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        variables_by_requirement: dict[
            UUID,
            list[cp_model.IntVar],
        ] = defaultdict(list)

        for variable in variables:

            variables_by_requirement[
                variable.lesson_requirement_id
            ].append(
                variable.variable
            )

        for requirement in problem.lesson_requirements:

            if not requirement.is_active:
                continue

            requirement_variables = (
                variables_by_requirement.get(
                    requirement.id,
                    [],
                )
            )

            model.add(
                sum(requirement_variables)
                == requirement.periods_per_week
            )

    # ------------------------------------------------------------------
    # ONE OCCURRENCE PER REQUIREMENT / SLOT
    # ------------------------------------------------------------------

    def _add_lesson_requirement_slot_constraints(
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
                    variable.lesson_requirement_id,
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

    # ------------------------------------------------------------------
    # TEACHER CLASHES
    # ------------------------------------------------------------------

    def _add_teacher_clash_constraints(
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

    # ------------------------------------------------------------------
    # INSTRUCTIONAL GROUP CLASHES
    # ------------------------------------------------------------------

    def _add_group_clash_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Ordinary subjects cannot occupy the same period for a group.

        Grade 10 simultaneous-option subjects are excluded because the
        students deliberately split into different elective pathways.
        """

        requirement_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        ordinary_groups: dict[
            tuple[UUID, str, UUID],
            list[cp_model.IntVar],
        ] = defaultdict(list)

        for variable in variables:

            requirement = requirement_by_id.get(
                variable.lesson_requirement_id
            )

            if requirement is None:
                continue

            if self._requirement_block(
                requirement,
                problem,
            ) is not None:
                continue

            ordinary_groups[
                (
                    variable.instructional_group_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(
                variable.variable
            )

        for grouped_variables in ordinary_groups.values():
            model.add_at_most_one(
                grouped_variables
            )

    # ------------------------------------------------------------------
    # SIMULTANEOUS GRADE 10 OPTION BLOCKS
    # ------------------------------------------------------------------

    def _add_simultaneous_option_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Enforce simultaneous placement of the original Grade 10 option blocks.

        AGRI + BS
        BIO + MUS + FRE
        CHEM + PHY + LIT
        GEO + HIST + CS

        Each requirement keeps its own teacher and room.

        Only the day/period presence is synchronized.
        """

        requirement_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        requirements_by_block: dict[
            frozenset[str],
            dict[str, object],
        ] = {}

        for requirement in problem.lesson_requirements:

            if not requirement.is_active:
                continue

            block = self._requirement_block(
                requirement,
                problem,
            )

            if block is None:
                continue

            subject = self._requirement_subject_code(
                requirement
            )

            if not subject:
                continue

            block_data = requirements_by_block.setdefault(
                block,
                {},
            )

            # Keep exactly one requirement for each subject.
            if subject not in block_data:
                block_data[subject] = requirement

        variables_by_requirement_slot: dict[
            tuple[UUID, str, UUID],
            list[cp_model.IntVar],
        ] = defaultdict(list)

        for variable in variables:

            variables_by_requirement_slot[
                (
                    variable.lesson_requirement_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(
                variable.variable
            )

        # --------------------------------------------------------------
        # Process every authoritative block.
        # --------------------------------------------------------------

        for block in SIMULTANEOUS_OPTION_BLOCKS:

            members = requirements_by_block.get(
                block,
                {},
            )

            # Do not manufacture requirements that do not exist.
            # The loader/database remains the source of lesson definitions.
            if len(members) < 2:
                continue

            requirements = [
                members[subject]
                for subject in block
                if subject in members
            ]

            if len(requirements) < 2:
                continue

            # A simultaneous block can only be synchronized when its
            # participating requirements have the same weekly frequency.
            #
            # If frequencies differ, forcing identical weekly presence
            # patterns would make the model mathematically infeasible.
            frequencies = {
                int(requirement.periods_per_week)
                for requirement in requirements
            }

            if len(frequencies) != 1:
                continue

            presence_by_requirement_slot: dict[
                tuple[UUID, str, UUID],
                cp_model.IntVar,
            ] = {}

            for requirement in requirements:

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

                    key = (
                        requirement.id,
                        slot.day.value,
                        slot.period_id,
                    )

                    assignment_variables = (
                        variables_by_requirement_slot.get(
                            key,
                            [],
                        )
                    )

                    presence = model.new_bool_var(
                        "simultaneous_presence_"
                        f"{requirement.id}_"
                        f"{slot.day.value}_"
                        f"{slot.period_id}"
                    )

                    presence_by_requirement_slot[key] = presence

                    if assignment_variables:

                        model.add(
                            sum(assignment_variables)
                            == presence
                        )

                    else:

                        model.add(
                            presence == 0
                        )

            anchor = requirements[0]

            for other in requirements[1:]:

                for slot in problem.slots:

                    anchor_key = (
                        anchor.id,
                        slot.day.value,
                        slot.period_id,
                    )

                    other_key = (
                        other.id,
                        slot.day.value,
                        slot.period_id,
                    )

                    anchor_presence = (
                        presence_by_requirement_slot.get(
                            anchor_key
                        )
                    )

                    other_presence = (
                        presence_by_requirement_slot.get(
                            other_key
                        )
                    )

                    if (
                        anchor_presence is None
                        or other_presence is None
                    ):
                        continue

                    model.add(
                        anchor_presence
                        == other_presence
                    )

    # ------------------------------------------------------------------
    # ROOM CLASHES
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # TEACHER AVAILABILITY
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # MANDATORY TEACHER FREE AFTERNOON
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # ROOM AVAILABILITY
    # ------------------------------------------------------------------

    def _add_room_availability_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

        active_availability = [
            availability
            for availability in problem.room_availability
            if availability.is_active
        ]

        configured_rooms = {
            availability.room_id
            for availability in active_availability
        }

        available_slots_by_room: dict[
            UUID,
            set[tuple[str, UUID]],
        ] = defaultdict(set)

        for availability in active_availability:

            if not availability.is_available:
                continue

            available_slots_by_room[
                availability.room_id
            ].add(
                (
                    availability.day.value,
                    availability.period_id,
                )
            )

        for variable in variables:

            if variable.room_id is None:
                continue

            if variable.room_id not in configured_rooms:
                continue

            key = (
                variable.day,
                variable.period_id,
            )

            if key not in available_slots_by_room[
                variable.room_id
            ]:

                model.add(
                    variable.variable == 0
                )

