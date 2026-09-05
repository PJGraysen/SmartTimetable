from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.enums import PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.objective import apply_solver_objectives
from apps.scheduling.engine.solver.variables import AssignmentVariable
from apps.scheduling.engine.application.grade10_parallel_blocks import GRADE10_PARALLEL_BLOCKS

# ------------------------------------------------------------------
# Grade 10 synchronized curriculum blocks
# ------------------------------------------------------------------
#
# These are LOGICAL scheduling blocks over the existing subject
# requirements. They do not create or modify database entities.
#
# OPT1 = BIO / MUSIC / FRE
# OPT2 = CHEM / PHY / LIT
# OPT3 = GEO / HIS / COMP
#
# Mathematics is a separate synchronized block:
# EC / CM
# ------------------------------------------------------------------

GRADE10_SYNCHRONIZED_BLOCKS: tuple[frozenset[str], ...] = ()


def _normalized_subject_code(requirement) -> str | None:
    code = getattr(requirement, "subject_code", None)

    if code is None:
        return None

    return str(code).strip().upper()


def _synchronized_block_for_subject(
    subject_code: str | None,
) -> frozenset[str] | None:
    if not subject_code:
        return None

    normalized = subject_code.strip().upper()

    for block in GRADE10_SYNCHRONIZED_BLOCKS:
        if normalized in block:
            return block

    return None



# ------------------------------------------------------------------
# Grade 10 synchronized option blocks
#
# These are the established simultaneous subject combinations:
#
# OPT1 = BIO / MUSIC / FRE
# OPT2 = CHEM / PHY / LIT
# OPT3 = GEO / HIS / COMP
#
# Synchronization is enforced by exact day + period.
# Teacher assignments remain independent and database-driven.
# ------------------------------------------------------------------

GRADE10_OPTION_BLOCKS: tuple[frozenset[str], ...] = tuple(
    frozenset(block.subject_codes)
    for block in GRADE10_PARALLEL_BLOCKS
)

def option_block_for_subject(
    subject_code: str | None,
) -> frozenset[str] | None:
    """Return the established Grade 10 option block for a subject code."""

    if not subject_code:
        return None

    normalized = subject_code.strip().upper()

    for block in GRADE10_OPTION_BLOCKS:
        if normalized in block:
            return block

    return None




# ============================================================================
# AUTHORITATIVE SIMULTANEOUS SUBJECT BLOCKS
# ============================================================================
#
# Subjects in the same block may occupy the same instructional-group/day/
# period because they represent simultaneous subject-combination teaching.
#
# Teacher assignments remain independent.
# Room assignments remain independent.
#
# IMPORTANT:
# EMCM is a single Grade 10 mathematics requirement.
# There is deliberately NO CM/EM simultaneous block.
# ============================================================================

SIMULTANEOUS_SUBJECT_GROUPS: tuple[frozenset[str], ...] = ()


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
    ):
        """Return variables belonging to one lesson requirement."""
        return tuple(
            variable
            for variable in self.variables
            if variable.lesson_requirement_id == lesson_requirement_id
        )


class SolverModelBuilder:
    """
    Builds a CP-SAT model from a validated SchedulingProblem.

    This class translates the domain problem into:

    1. Assignment variables
    2. Exact weekly lesson requirements
    3. Teacher clash constraints
    4. Teaching-group clash constraints
    5. Simultaneous subject-combination constraints
    6. Room clash constraints
    7. Teacher availability constraints
    8. Mandatory teacher free-afternoon constraints
    9. Room availability constraints

    The objective parameter is retained for compatibility with the
    application scheduler. Objective construction remains the responsibility
    of the scheduler/objective subsystem.
    """

    def __init__(self, objective=None):
        self.objective = objective

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

        self._add_grade10_option_block_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

        self._add_simultaneous_subject_constraints(
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

        self._add_single_lesson_per_day_constraints(
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
    # Variable creation
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

            # ----------------------------------------------------------
            # Teacher-independent placement:
            #
            # A requirement with no active teacher still receives real
            # timetable placement variables. These variables carry
            # teacher_id=None and therefore represent class placement,
            # not a teacher assignment.
            #
            # This is required for Grade 10 FRE and GST/LF.
            # ----------------------------------------------------------

            teacher_options: list[UUID | None] = (
                eligible_teacher_ids
                if eligible_teacher_ids
                else [None]
            )

            for teacher_id in teacher_options:

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

                        teacher_token = (
                            str(teacher_id)
                            if teacher_id is not None
                            else "NO_TEACHER"
                        )

                        name = (
                            f"assign_"
                            f"{requirement.id}_"
                            f"{teacher_token}_"
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

    def _add_lesson_requirement_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """Enforce the weekly quota for each active lesson requirement.

        Core subjects and non-option requirements retain their exact
        ``periods_per_week`` quota.

        Grade 10 option subjects are different: BIO/MUS/FRE, CHEM/PHY/LIT,
        GEO/HIS/CS, and BUS/AGR are alternatives inside a shared five-slot
        physical block.  Their individual database rows describe the
        available alternatives, not five simultaneous lessons each.

        Therefore the model enforces the five-slot quota at block level for
        Grade 10 and does not impose an individual exact quota on each
        alternative.
        """
        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        variables_by_requirement: dict[UUID, list[AssignmentVariable]] = defaultdict(list)

        for variable in variables:
            if variable.lesson_requirement_id in requirements_by_id:
                variables_by_requirement[variable.lesson_requirement_id].append(variable)

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
        }

        # Collect Grade 10 option variables by physical block.
        grade10_block_variables: dict[
            tuple[UUID, str],
            list[AssignmentVariable],
        ] = defaultdict(list)

        for requirement_id, requirement_variables in variables_by_requirement.items():
            requirement = requirements_by_id[requirement_id]
            block = option_block_for_subject(requirement.subject_code)
            group = groups_by_id.get(requirement.instructional_group_id)

            if (
                block is not None
                and group is not None
                and self._is_grade10_group(group)
            ):
                grade10_block_variables[
                    (requirement.instructional_group_id, self._grade10_block_code(block))
                ].extend(requirement_variables)

        grade10_requirement_ids = {
            requirement.id
            for requirement in requirements_by_id.values()
            if (
                option_block_for_subject(requirement.subject_code) is not None
                and self._is_grade10_group(
                    groups_by_id.get(requirement.instructional_group_id)
                )
            )
        }

        # Ordinary requirements keep their exact weekly quota.
        for requirement_id, requirement in requirements_by_id.items():
            if requirement_id in grade10_requirement_ids:
                continue

            requirement_variables = variables_by_requirement.get(requirement_id, [])
            model.add(
                sum(variable.variable for variable in requirement_variables)
                == requirement.periods_per_week
            )

        # Each Grade 10 option block occupies exactly five physical lessons.
        for (group_id, block_code), block_variables in grade10_block_variables.items():
            if not block_variables:
                continue

            block = next(
                block_definition
                for block_definition in GRADE10_PARALLEL_BLOCKS
                if block_definition.code == block_code
            )

            model.add(
                sum(variable.variable for variable in block_variables)
                == block.weekly_shared_slots
            )

    def _is_grade10_group(self, group: object | None) -> bool:
        """Return True only for the Grade 10 instructional groups."""
        if group is None:
            return False

        for attribute in ("code", "name"):
            value = getattr(group, attribute, None)
            if value is None:
                continue

            normalized = str(value).strip().upper().replace("-", " ")
            if normalized in {"10E", "10W", "GRADE 10E", "GRADE 10W"}:
                return True

        return False

    @staticmethod
    def _grade10_block_code(block: frozenset[str]) -> str:
        """Map an established option subject set to its authoritative block."""
        for block_definition in GRADE10_PARALLEL_BLOCKS:
            if frozenset(block_definition.subject_codes) == block:
                return block_definition.code

        raise ValueError(
            f"Unknown Grade 10 option block: {sorted(block)}"
        )

    def _add_single_lesson_per_day_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """Do not repeat one requirement on a day without explicit data."""

        variables_by_requirement_day: dict[
            tuple[UUID, str], list[cp_model.IntVar]
        ] = defaultdict(list)

        for variable in variables:
            variables_by_requirement_day[
                (variable.lesson_requirement_id, variable.day)
            ].append(variable.variable)

        active_requirement_ids = {
            requirement.id
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        for (requirement_id, _day), day_variables in (
            variables_by_requirement_day.items()
        ):
            if requirement_id in active_requirement_ids:
                model.add_at_most_one(day_variables)

    # ------------------------------------------------------------------
    # Simultaneous subject combinations
    # ------------------------------------------------------------------

    def _add_simultaneous_subject_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Force members of the same configured subject combination to
        occupy exactly the same day/period slots for the same
        instructional group.

        Teacher assignments remain independent.

        Room assignments remain independent.

        Each requirement retains its own weekly lesson count.
        """

        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        variables_by_requirement: dict[
            UUID,
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            if variable.lesson_requirement_id in requirements_by_id:
                variables_by_requirement[
                    variable.lesson_requirement_id
                ].append(variable)

        requirements_by_block: dict[
            tuple[UUID, frozenset[str]],
            list[UUID],
        ] = defaultdict(list)

        for requirement in requirements_by_id.values():

            block = simultaneous_group_for_subject(
                requirement.subject_code
            )

            if block is None:
                continue

            requirements_by_block[
                (
                    requirement.instructional_group_id,
                    block,
                )
            ].append(
                requirement.id
            )

        for (
            instructional_group_id,
            block,
        ), requirement_ids in requirements_by_block.items():

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
                    "weekly lesson counts for instructional group "
                    f"{instructional_group_id}: "
                    f"{sorted(weekly_counts)}."
                )

            slot_keys = {
                (
                    variable.day,
                    variable.period_id,
                )
                for requirement_id in requirement_ids
                for variable in variables_by_requirement[
                    requirement_id
                ]
            }

            for day, period_id in slot_keys:

                slot_variables_by_requirement: dict[
                    UUID,
                    list[cp_model.IntVar],
                ] = {}

                for requirement_id in requirement_ids:

                    slot_variables_by_requirement[
                        requirement_id
                    ] = [
                        variable.variable
                        for variable in variables_by_requirement[
                            requirement_id
                        ]
                        if (
                            variable.day == day
                            and variable.period_id == period_id
                        )
                    ]

                    model.add_at_most_one(
                        slot_variables_by_requirement[
                            requirement_id
                        ]
                    )

                first_requirement_id = requirement_ids[0]

                first_slot_expression = sum(
                    slot_variables_by_requirement[
                        first_requirement_id
                    ]
                )

                for other_requirement_id in requirement_ids[1:]:

                    other_slot_expression = sum(
                        slot_variables_by_requirement[
                            other_requirement_id
                        ]
                    )

                    model.add(
                        first_slot_expression
                        == other_slot_expression
                    )

    # ------------------------------------------------------------------
    # Teacher clashes
    # ------------------------------------------------------------------

    def _add_grade10_option_block_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """Keep Grade 10 alternatives inside each option block mutually exclusive.

        The five weekly physical slots for a block are shared by its
        alternatives.  At any particular group/day/period, at most one
        subject from that block may be placed.

        This does not require BIO+MUS+FRE (or the other alternatives) to occur
        simultaneously.  It only prevents two alternatives from occupying the
        same physical lesson slot.
        """
        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
        }

        block_slot_variables: dict[
            tuple[UUID, str, UUID, frozenset[str]],
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            requirement = requirements_by_id.get(variable.lesson_requirement_id)
            if requirement is None:
                continue

            group = groups_by_id.get(variable.instructional_group_id)
            if not self._is_grade10_group(group):
                continue

            block = option_block_for_subject(requirement.subject_code)
            if block is None:
                continue

            block_slot_variables[
                (
                    variable.instructional_group_id,
                    variable.day,
                    variable.period_id,
                    block,
                )
            ].append(variable)

        for slot_variables in block_slot_variables.values():
            model.add(
                sum(variable.variable for variable in slot_variables) <= 1
            )

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

            # A teacherless placement has no teacher resource to clash
            # with. Its group and room are still constrained normally.
            if variable.teacher_id is None:
                continue

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

    def _add_group_clash_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Prevent unrelated subjects from occupying the same
        instructional-group/day/period.

        Explicit simultaneous subject combinations are the only
        exception.

        A single lesson requirement can never be duplicated inside
        one instructional-group/day/period through multiple
        teacher/room alternatives.
        """

        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
        }

        slots: dict[
            tuple[UUID, str, UUID],
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:

            slots[
                (
                    variable.instructional_group_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(variable)

        for grouped_variables in slots.values():

            variables_by_requirement: dict[
                UUID,
                list[cp_model.IntVar],
            ] = defaultdict(list)

            variables_by_block: dict[
                frozenset[str] | None,
                list[cp_model.IntVar],
            ] = defaultdict(list)

            requirement_block: dict[
                UUID,
                frozenset[str] | None,
            ] = {}

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

                requirement_block[
                    variable.lesson_requirement_id
                ] = block

                variables_by_requirement[
                    variable.lesson_requirement_id
                ].append(
                    variable.variable
                )

                variables_by_block[block].append(
                    variable.variable
                )

            # A single lesson requirement can only have one selected
            # teacher/room assignment in one group/day/period.
            for requirement_variables in (
                variables_by_requirement.values()
            ):
                model.add_at_most_one(
                    requirement_variables
                )

            ordinary_requirements = [
                requirement_id
                for requirement_id, block
                in requirement_block.items()
                if block is None
            ]

            simultaneous_blocks = list(
                {
                    block
                    for block in requirement_block.values()
                    if block is not None
                }
            )

            # Ordinary subjects are mutually exclusive.
            if ordinary_requirements:
                model.add_at_most_one(
                    [
                        variable.variable
                        for variable in grouped_variables
                        if requirement_block.get(
                            variable.lesson_requirement_id
                        ) is None
                    ]
                )

            # An ordinary subject cannot overlap a simultaneous block.
            for ordinary_requirement_id in ordinary_requirements:

                ordinary_variables = (
                    variables_by_requirement[
                        ordinary_requirement_id
                    ]
                )

                for block in simultaneous_blocks:

                    block_variables = variables_by_block[
                        block
                    ]

                    for ordinary_variable in ordinary_variables:

                        for block_variable in block_variables:

                            model.add_at_most_one(
                                [
                                    ordinary_variable,
                                    block_variable,
                                ]
                            )

            # Two different simultaneous blocks cannot overlap.
            for index, first_block in enumerate(
                simultaneous_blocks
            ):

                for second_block in simultaneous_blocks[
                    index + 1:
                ]:

                    first_variables = variables_by_block[
                        first_block
                    ]

                    second_variables = variables_by_block[
                        second_block
                    ]

                    for first_variable in first_variables:

                        for second_variable in second_variables:

                            model.add_at_most_one(
                                [
                                    first_variable,
                                    second_variable,
                                ]
                            )

    # ------------------------------------------------------------------
    # Room clashes
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
    # Teacher availability
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

            # No teacher means there is no teacher availability rule
            # to apply yet. The class placement remains constrained by
            # group, room and timetable-slot rules.
            if variable.teacher_id is None:
                continue

            key = (
                variable.teacher_id,
                variable.day,
                variable.period_id,
            )

            if key in unavailable_slots:
                model.add(
                    variable.variable == 0
                )

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

            free_afternoon = problem.teacher_free_afternoon(
                teacher.id
            )

            if free_afternoon is None:
                raise ValueError(
                    f"Teacher {teacher.id} has no free-afternoon assignment."
                )

            for variable in variables:

                if variable.teacher_id is None:
                    continue

                if variable.teacher_id != teacher.id:
                    continue

                if variable.day != free_afternoon.day.value:
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

                if period.part_of_day != PartOfDay.AFTERNOON:
                    continue

                model.add(variable.variable == 0)

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
