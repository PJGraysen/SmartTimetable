from __future__ import annotations

from datetime import time
from uuid import uuid4

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.entities import (
    LessonRequirementEntity,
    PeriodEntity,
    TeacherEntity,
    TeacherFreeAfternoonEntity,
    TeachingGroupEntity,
    TimetableSlot,
)
from apps.scheduling.engine.domain.enums import (
    DayOfWeek,
    PartOfDay,
)
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.objective import (
    TeacherConsecutivePeriodObjective,
)
from apps.scheduling.engine.solver.variables import AssignmentVariable


def _teacher(code: str = "T001") -> TeacherEntity:
    return TeacherEntity(
        id=uuid4(),
        name="Test Teacher",
        code=code,
        is_active=True,
    )


def _group() -> TeachingGroupEntity:
    return TeachingGroupEntity(
        id=uuid4(),
        name="Test Group",
        code="G001",
        is_active=True,
    )


def _period(number: int) -> PeriodEntity:
    start_minutes = 8 * 60 + (number - 1) * 40
    end_minutes = start_minutes + 40

    start_hour, start_minute = divmod(start_minutes, 60)
    end_hour, end_minute = divmod(end_minutes, 60)

    return PeriodEntity(
        id=uuid4(),
        number=number,
        name=f"Period {number}",
        start_time=time(
            hour=start_hour,
            minute=start_minute,
        ),
        end_time=time(
            hour=end_hour,
            minute=end_minute,
        ),
        part_of_day=PartOfDay.MORNING,
        is_teaching_period=True,
        is_active=True,
    )


def _requirement(
    group: TeachingGroupEntity,
) -> LessonRequirementEntity:
    return LessonRequirementEntity(
        id=uuid4(),
        teaching_group_id=group.id,
        subject_id=uuid4(),
        periods_per_week=2,
        is_active=True,
    )


def _free_afternoon(
    teacher: TeacherEntity,
) -> TeacherFreeAfternoonEntity:
    return TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
        is_active=True,
    )


def _problem(
    *,
    teachers: tuple[TeacherEntity, ...],
    groups: tuple[TeachingGroupEntity, ...],
    periods: tuple[PeriodEntity, ...],
    requirements: tuple[LessonRequirementEntity, ...],
) -> SchedulingProblem:
    slots = tuple(
        TimetableSlot(
            day=DayOfWeek.MONDAY,
            period_id=period.id,
            period_number=period.number,
            part_of_day=period.part_of_day,
        )
        for period in periods
    )

    teacher_free_afternoons = tuple(
        _free_afternoon(teacher)
        for teacher in teachers
        if teacher.is_active
    )

    return SchedulingProblem(
        periods=periods,
        slots=slots,
        teachers=teachers,
        teaching_groups=groups,
        rooms=tuple(),
        lesson_requirements=requirements,
        teacher_assignments=tuple(),
        teacher_availability=tuple(),
        teacher_free_afternoons=teacher_free_afternoons,
        room_availability=tuple(),
    )


def _variables(
    *,
    model: cp_model.CpModel,
    teacher: TeacherEntity,
    requirement: LessonRequirementEntity,
    periods: tuple[PeriodEntity, ...],
) -> tuple[AssignmentVariable, ...]:
    return tuple(
        AssignmentVariable(
            lesson_requirement_id=requirement.id,
            teacher_id=teacher.id,
            teaching_group_id=requirement.teaching_group_id,
            period_id=period.id,
            day=DayOfWeek.MONDAY.value,
            room_id=None,
            variable=model.new_bool_var(
                f"assignment_period_{period.number}"
            ),
        )
        for period in periods
    )


def _solve(
    model: cp_model.CpModel,
) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    )

    return solver


def test_consecutive_period_objective_rejects_invalid_weight():
    try:
        TeacherConsecutivePeriodObjective(weight=0)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError for non-positive weight."
        )


def test_consecutive_period_objective_accepts_valid_weight():
    objective = TeacherConsecutivePeriodObjective(weight=1)

    assert objective.weight == 1


def test_consecutive_period_objective_penalizes_consecutive_assignments():
    teacher = _teacher()
    group = _group()
    requirement = _requirement(group)

    periods = (
        _period(1),
        _period(2),
    )

    model = cp_model.CpModel()

    variables = _variables(
        model=model,
        teacher=teacher,
        requirement=requirement,
        periods=periods,
    )

    model.add(variables[0].variable == 1)
    model.add(variables[1].variable == 1)

    problem = _problem(
        teachers=(teacher,),
        groups=(group,),
        periods=periods,
        requirements=(requirement,),
    )

    objective = TeacherConsecutivePeriodObjective(weight=1)

    objective.apply(
        model=model,
        problem=problem,
        variables=variables,
    )

    solver = _solve(model)

    assert solver.objective_value > 0


def test_consecutive_period_objective_prefers_non_consecutive_schedule():
    teacher = _teacher()
    group = _group()
    requirement = _requirement(group)

    periods = (
        _period(1),
        _period(2),
        _period(3),
    )

    model = cp_model.CpModel()

    variables = _variables(
        model=model,
        teacher=teacher,
        requirement=requirement,
        periods=periods,
    )

    model.add(
        sum(
            variable.variable
            for variable in variables
        )
        == 2
    )

    problem = _problem(
        teachers=(teacher,),
        groups=(group,),
        periods=periods,
        requirements=(requirement,),
    )

    objective = TeacherConsecutivePeriodObjective(weight=1)

    objective.apply(
        model=model,
        problem=problem,
        variables=variables,
    )

    solver = _solve(model)

    assert solver.value(variables[0].variable) == 1
    assert solver.value(variables[1].variable) == 0
    assert solver.value(variables[2].variable) == 1


def test_consecutive_period_objective_does_not_penalize_non_adjacent_periods():
    teacher = _teacher()
    group = _group()
    requirement = _requirement(group)

    periods = (
        _period(1),
        _period(2),
        _period(3),
    )

    model = cp_model.CpModel()

    variables = _variables(
        model=model,
        teacher=teacher,
        requirement=requirement,
        periods=periods,
    )

    model.add(variables[0].variable == 1)
    model.add(variables[1].variable == 0)
    model.add(variables[2].variable == 1)

    problem = _problem(
        teachers=(teacher,),
        groups=(group,),
        periods=periods,
        requirements=(requirement,),
    )

    objective = TeacherConsecutivePeriodObjective(weight=1)

    objective.apply(
        model=model,
        problem=problem,
        variables=variables,
    )

    solver = _solve(model)

    assert solver.objective_value == 0


def test_consecutive_period_objective_does_not_penalize_different_teachers():
    teacher_one = _teacher("T001")
    teacher_two = _teacher("T002")

    group = _group()

    requirement_one = _requirement(group)
    requirement_two = _requirement(group)

    periods = (
        _period(1),
        _period(2),
    )

    model = cp_model.CpModel()

    variables = (
        AssignmentVariable(
            lesson_requirement_id=requirement_one.id,
            teacher_id=teacher_one.id,
            teaching_group_id=group.id,
            period_id=periods[0].id,
            day=DayOfWeek.MONDAY.value,
            room_id=None,
            variable=model.new_bool_var(
                "teacher_one_period_one"
            ),
        ),
        AssignmentVariable(
            lesson_requirement_id=requirement_two.id,
            teacher_id=teacher_two.id,
            teaching_group_id=group.id,
            period_id=periods[1].id,
            day=DayOfWeek.MONDAY.value,
            room_id=None,
            variable=model.new_bool_var(
                "teacher_two_period_two"
            ),
        ),
    )

    model.add(variables[0].variable == 1)
    model.add(variables[1].variable == 1)

    problem = _problem(
        teachers=(teacher_one, teacher_two),
        groups=(group,),
        periods=periods,
        requirements=(
            requirement_one,
            requirement_two,
        ),
    )

    objective = TeacherConsecutivePeriodObjective(weight=1)

    objective.apply(
        model=model,
        problem=problem,
        variables=variables,
    )

    solver = _solve(model)

    assert solver.objective_value == 0


def test_consecutive_period_objective_does_not_penalize_different_days():
    teacher = _teacher()
    group = _group()
    requirement = _requirement(group)

    periods = (
        _period(1),
        _period(2),
    )

    model = cp_model.CpModel()

    variables = (
        AssignmentVariable(
            lesson_requirement_id=requirement.id,
            teacher_id=teacher.id,
            teaching_group_id=group.id,
            period_id=periods[0].id,
            day=DayOfWeek.MONDAY.value,
            room_id=None,
            variable=model.new_bool_var(
                "monday_period_one"
            ),
        ),
        AssignmentVariable(
            lesson_requirement_id=requirement.id,
            teacher_id=teacher.id,
            teaching_group_id=group.id,
            period_id=periods[1].id,
            day=DayOfWeek.TUESDAY.value,
            room_id=None,
            variable=model.new_bool_var(
                "tuesday_period_two"
            ),
        ),
    )

    model.add(variables[0].variable == 1)
    model.add(variables[1].variable == 1)

    problem = _problem(
        teachers=(teacher,),
        groups=(group,),
        periods=periods,
        requirements=(requirement,),
    )

    objective = TeacherConsecutivePeriodObjective(weight=1)

    objective.apply(
        model=model,
        problem=problem,
        variables=variables,
    )

    solver = _solve(model)

    assert solver.objective_value == 0
