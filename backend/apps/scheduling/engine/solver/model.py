from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.enums import PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.variables import AssignmentVariable


@dataclass(slots=True)
class SolverModel:
    """
    CP-SAT model together with the assignment variables created for it.
    """

    model: cp_model.CpModel
    variables: tuple[AssignmentVariable, ...]

    def variables_for_lesson(self, lesson_requirement_id: UUID):
        """Return variables belonging to one lesson requirement."""
        return tuple(
            variable
            for variable in self.variables
            if variable.lesson_requirement_id == lesson_requirement_id
        )


class SolverModelBuilder:
    """
    Builds a CP-SAT model from a validated SchedulingProblem.

    This class is responsible for translating the domain problem into
    solver variables and hard constraints.
    """

    def build(self, problem: SchedulingProblem) -> SolverModel:
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

        self._add_teacher_clash_constraints(
            model=model,
            variables=variables,
        )

        self._add_group_clash_constraints(
            model=model,
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
            for group in problem.teaching_groups
            if group.is_active
        ]

        active_rooms = [
            room
            for room in problem.rooms
            if room.is_active
        ]

        teachers_by_requirement: dict[
            UUID, list[UUID]
        ] = defaultdict(list)

        for assignment in problem.teacher_assignments:
            if not assignment.is_active:
                continue

            teachers_by_requirement[
                assignment.lesson_requirement_id
            ].append(assignment.teacher_id)

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

            if requirement.teaching_group_id not in valid_group_ids:
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

                    period = problem.period_by_id.get(slot.period_id)

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
                                teaching_group_id=(
                                    requirement.teaching_group_id
                                ),
                                period_id=slot.period_id,
                                day=slot.day.value,
                                room_id=room.id,
                                variable=variable,
                            )
                        )

        return variables

       # ------------------------------------------------------------------
    # Lesson requirements
    # ------------------------------------------------------------------

    def _add_lesson_requirement_constraints(
        self,
        *,
        model: cp_model.CpModel,
        problem: SchedulingProblem,
        variables: list[AssignmentVariable],
    ) -> None:

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

            model.add(
                sum(requirement_variables)
                == requirement.periods_per_week
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
            ].append(variable.variable)

        for grouped_variables in groups.values():
            model.add_at_most_one(grouped_variables)

    # ------------------------------------------------------------------
    # Teaching-group clashes
    # ------------------------------------------------------------------

    def _add_group_clash_constraints(
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
                    variable.teaching_group_id,
                    variable.day,
                    variable.period_id,
                )
            ].append(variable.variable)

        for grouped_variables in groups.values():
            model.add_at_most_one(grouped_variables)

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
            ].append(variable.variable)

        for grouped_variables in groups.values():
            model.add_at_most_one(grouped_variables)

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
                model.add(variable.variable == 0)

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

                # HARD CONSTRAINT:
                # teacher cannot teach during their designated
                # free afternoon.
                model.add(variable.variable == 0)

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
                model.add(variable.variable == 0)
