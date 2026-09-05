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

        self._add_institutional_reserved_period_constraints(
            model=model,
            problem=problem,
            variables=variables,
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
    # Institutional reserved periods
    # ------------------------------------------------------------------

    def _add_institutional_reserved_period_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Enforce mandatory institutional reserved periods.

        Monday 08:00-08:40 (database period number 1) is reserved
        for the whole-school morning Assembly / weekly briefing.

        It is therefore not a lesson-placement slot for any
        instructional group, teacher, subject, or room.

        The physical Period record remains part of the timetable
        structure; this constraint controls lesson eligibility.
        """

        period_numbers = {
            period.id: period.number
            for period in problem.periods
        }

        for variable in variables:
            day = str(variable.day).strip().upper()

            if day not in {"MON", "MONDAY"}:
                continue

            if period_numbers.get(variable.period_id) != 1:
                continue

            model.add(variable.variable == 0)

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
        """
        Enforce the authoritative weekly quota for every active requirement.

        Grade 10 elective subjects are NOT alternatives.

        Every subject in every Grade 10 option block receives its own
        five lessons per instructional group. The subjects in a block
        subsequently share the same five physical day/period cells through
        _add_grade10_option_block_constraints().

        Thus, for example:

            BIO = 5
            MUS = 5
            FRE = 5

        while those 15 subject entries occupy only five physical cells.

        Teacher and room assignments remain independent.
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

        for requirement_id, requirement in requirements_by_id.items():
            requirement_variables = variables_by_requirement.get(
                requirement_id,
                [],
            )

            model.add(
                sum(
                    variable.variable
                    for variable in requirement_variables
                )
                == requirement.periods_per_week
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
        """
        Enforce the authoritative Grade 10 parallel-elective structure.

        Each subject requirement in an option block receives its own
        weekly quota. All subjects belonging to that block must occupy
        exactly the same five instructional-group/day/period cells.

        Example:

            OPTION 1 = BIO / MUS / FRE

        produces:

            BIO -> 5 placements
            MUS -> 5 placements
            FRE -> 5 placements

        but those placements are synchronized onto the same five
        physical timetable cells.

        Teacher assignments remain independent.
        Room assignments remain independent.

        The block therefore represents parallel teaching, not a choice
        between subjects.
        """
        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if group.is_active
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

        block_requirements: dict[
            tuple[UUID, str],
            list[UUID],
        ] = defaultdict(list)

        for requirement in requirements_by_id.values():
            group = groups_by_id.get(
                requirement.instructional_group_id
            )

            if not self._is_grade10_group(group):
                continue

            block = option_block_for_subject(
                requirement.subject_code
            )

            if block is None:
                continue

            block_code = self._grade10_block_code(block)

            block_requirements[
                (
                    requirement.instructional_group_id,
                    block_code,
                )
            ].append(requirement.id)

        for (
            instructional_group_id,
            block_code,
        ), requirement_ids in block_requirements.items():

            block_definition = next(
                (
                    definition
                    for definition in GRADE10_PARALLEL_BLOCKS
                    if definition.code == block_code
                ),
                None,
            )

            if block_definition is None:
                raise ValueError(
                    "Missing Grade 10 option block definition: "
                    f"{block_code}"
                )

            expected_subject_codes = {
                str(code).strip().upper()
                for code in block_definition.subject_codes
            }

            actual_subject_codes = {
                str(
                    requirements_by_id[
                        requirement_id
                    ].subject_code
                ).strip().upper()
                for requirement_id in requirement_ids
            }

            missing_subjects = (
                expected_subject_codes
                - actual_subject_codes
            )

            if missing_subjects:
                raise ValueError(
                    "Grade 10 option block is incomplete for "
                    f"instructional group {instructional_group_id}. "
                    f"Block {block_code} is missing active requirements: "
                    f"{sorted(missing_subjects)}"
                )

            weekly_counts = {
                requirements_by_id[
                    requirement_id
                ].periods_per_week
                for requirement_id in requirement_ids
            }

            if weekly_counts != {
                block_definition.weekly_shared_slots
            }:
                raise ValueError(
                    "Grade 10 option block has an invalid weekly quota "
                    f"for group {instructional_group_id}, block "
                    f"{block_code}: {sorted(weekly_counts)}; "
                    f"expected {block_definition.weekly_shared_slots}."
                )

            variables_by_requirement_slot: dict[
                tuple[UUID, str, UUID],
                list[cp_model.IntVar],
            ] = defaultdict(list)

            for requirement_id in requirement_ids:
                for variable in variables_by_requirement[
                    requirement_id
                ]:
                    variables_by_requirement_slot[
                        (
                            requirement_id,
                            variable.day,
                            variable.period_id,
                        )
                    ].append(
                        variable.variable
                    )

            # One teacher/room assignment per subject in one cell.
            for requirement_id in requirement_ids:
                for variable in variables_by_requirement[
                    requirement_id
                ]:
                    pass

                for day in {
                    variable.day
                    for variable in variables_by_requirement[
                        requirement_id
                    ]
                }:
                    for period_id in {
                        variable.period_id
                        for variable in variables_by_requirement[
                            requirement_id
                        ]
                        if variable.day == day
                    }:
                        slot_variables = (
                            variables_by_requirement_slot.get(
                                (
                                    requirement_id,
                                    day,
                                    period_id,
                                ),
                                [],
                            )
                        )

                        if slot_variables:
                            model.add_at_most_one(
                                slot_variables
                            )

            # Every subject in the block must occupy exactly the same
            # day/period cells.
            first_requirement_id = requirement_ids[0]

            all_slot_keys = {
                (
                    variable.day,
                    variable.period_id,
                )
                for requirement_id in requirement_ids
                for variable in variables_by_requirement[
                    requirement_id
                ]
            }

            for day, period_id in all_slot_keys:
                first_expression = sum(
                    variables_by_requirement_slot.get(
                        (
                            first_requirement_id,
                            day,
                            period_id,
                        ),
                        [],
                    )
                )

                for other_requirement_id in requirement_ids[1:]:
                    other_expression = sum(
                        variables_by_requirement_slot.get(
                            (
                                other_requirement_id,
                                day,
                                period_id,
                            ),
                            [],
                        )
                    )

                    model.add(
                        first_expression
                        == other_expression
                    )

            # Explicitly require the shared physical block to contain
            # exactly the configured number of cells.
            first_requirement_variables = (
                variables_by_requirement[
                    first_requirement_id
                ]
            )

            model.add(
                sum(
                    variable.variable
                    for variable in first_requirement_variables
                )
                == block_definition.weekly_shared_slots
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
        Prevent unrelated subjects from sharing a physical group/day/period.

        Grade 10 option subjects are parallel: all subjects in one option
        block may occupy the same physical cell, while different blocks and
        ordinary subjects remain mutually exclusive.

        Presence variables are used at the requirement/block level instead
        of generating pairwise constraints across every teacher/room
        assignment variable. This preserves the scheduling semantics while
        substantially reducing CP-SAT model size.
        """
        requirements_by_id = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
        }

        groups_by_id = {
            group.id: group
            for group in problem.instructional_groups
            if group.is_active
        }

        cells: dict[
            tuple[UUID, str, UUID],
            list[AssignmentVariable],
        ] = defaultdict(list)

        for variable in variables:
            cells[
                (
                    variable.instructional_group_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(variable)

        for (
            instructional_group_id,
            day,
            period_id,
        ), cell_variables in cells.items():

            requirement_variables: dict[
                UUID,
                list[cp_model.IntVar],
            ] = defaultdict(list)

            requirement_blocks: dict[
                UUID,
                frozenset[str] | None,
            ] = {}

            group = groups_by_id.get(instructional_group_id)

            for variable in cell_variables:
                requirement = requirements_by_id.get(
                    variable.lesson_requirement_id
                )

                block = None

                if (
                    requirement is not None
                    and group is not None
                    and self._is_grade10_group(group)
                ):
                    block = option_block_for_subject(
                        requirement.subject_code
                    )

                requirement_id = variable.lesson_requirement_id

                requirement_variables[
                    requirement_id
                ].append(
                    variable.variable
                )

                requirement_blocks[
                    requirement_id
                ] = block

            requirement_presence: dict[
                UUID,
                cp_model.IntVar,
            ] = {}

            for requirement_id, requirement_vars in (
                requirement_variables.items()
            ):
                model.add_at_most_one(requirement_vars)

                presence = model.new_bool_var(
                    (
                        "cell_presence_"
                        f"{instructional_group_id}_"
                        f"{day}_"
                        f"{period_id}_"
                        f"{requirement_id}"
                    )
                )

                model.add(
                    presence == sum(requirement_vars)
                )

                requirement_presence[
                    requirement_id
                ] = presence

            ordinary_presence: list[cp_model.IntVar] = []

            block_requirement_ids: dict[
                frozenset[str],
                list[UUID],
            ] = defaultdict(list)

            for requirement_id, block in requirement_blocks.items():
                if block is None:
                    ordinary_presence.append(
                        requirement_presence[
                            requirement_id
                        ]
                    )
                else:
                    block_requirement_ids[
                        block
                    ].append(
                        requirement_id
                    )

            block_presence: list[cp_model.IntVar] = []

            for block, requirement_ids in (
                block_requirement_ids.items()
            ):
                if not requirement_ids:
                    continue

                representative_id = min(
                    requirement_ids,
                    key=str,
                )

                presence = model.new_bool_var(
                    (
                        "option_block_presence_"
                        f"{instructional_group_id}_"
                        f"{day}_"
                        f"{period_id}_"
                        f"{self._grade10_block_code(block)}"
                    )
                )

                # _add_grade10_option_block_constraints() already forces
                # every subject in the block to have identical presence
                # at each day/period. Therefore one representative
                # requirement is sufficient to represent the physical
                # block occupancy here.
                model.add(
                    presence
                    == requirement_presence[
                        representative_id
                    ]
                )

                block_presence.append(presence)

            # One ordinary requirement OR one Grade 10 option block may
            # occupy a physical instructional-group cell. Subjects inside
            # the same option block intentionally share that cell.
            model.add_at_most_one(
                ordinary_presence + block_presence
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
