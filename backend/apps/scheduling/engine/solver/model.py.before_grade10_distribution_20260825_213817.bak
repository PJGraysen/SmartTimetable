from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.enums import PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.variables import AssignmentVariable


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

SIMULTANEOUS_SUBJECT_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"BIO", "MUSIC", "FRE"}),
    frozenset({"CHEM", "PHY", "LIT"}),
    frozenset({"GEO", "HIS", "COMP"}),
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
    # Exact weekly lesson requirements
    # ------------------------------------------------------------------

    def _add_lesson_requirement_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:
        """
        Every active lesson requirement must be scheduled exactly
        periods_per_week times.

        If an active requirement has no candidate variables, the model
        is deliberately made infeasible rather than raising a Python
        exception. This preserves CP-SAT feasibility semantics and
        allows callers/tests to inspect the solver result.
        """

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
                model.add(
                    0 == required_count
                )
                continue

            model.add(
                sum(requirement_variables) == required_count
            )

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
    # Instructional-group clashes
    # ------------------------------------------------------------------

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
    # Mandatory teacher free afternoons
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

            free_afternoon = problem.teacher_free_afternoon(
                teacher.id
            )

            if free_afternoon is None:
                raise ValueError(
                    f"Teacher {teacher.id} has no free-afternoon assignment."
                )

            for variable in variables:

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

                model.add(
                    variable.variable == 0
                )

    # ------------------------------------------------------------------
    # Room availability
    # ------------------------------------------------------------------

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
