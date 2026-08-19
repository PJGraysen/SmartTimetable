from __future__ import annotations

from datetime import time
from uuid import uuid4

from apps.scheduling.engine.domain.entities import (
    LessonRequirementEntity,
    PeriodEntity,
    SchedulingAssignment,
    TeacherEntity,
    TeacherFreeAfternoonEntity,
    TeachingGroupEntity,
)
from apps.scheduling.engine.domain.enums import (
    DayOfWeek,
    PartOfDay,
    ValidationCategory,
    ValidationSeverity,
)
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.validation.validator import (
    TimetableValidator,
    validate,
    validate_timetable,
)


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


def make_period(
    *,
    number: int = 1,
    part_of_day: PartOfDay = PartOfDay.MORNING,
) -> PeriodEntity:
    return PeriodEntity(
        id=uuid4(),
        number=number,
        name=f"Period {number}",
        start_time=time(8, 0),
        end_time=time(8, 40),
        part_of_day=part_of_day,
        is_teaching_period=True,
    )


def make_teacher() -> TeacherEntity:
    return TeacherEntity(
        id=uuid4(),
        name="Teacher One",
        code="T001",
    )


def make_group() -> TeachingGroupEntity:
    return TeachingGroupEntity(
        id=uuid4(),
        name="Form 1A",
        code="F1A",
    )


def make_requirement(
    *,
    group_id,
    periods_per_week: int = 1,
) -> LessonRequirementEntity:
    return LessonRequirementEntity(
        id=uuid4(),
        teaching_group_id=group_id,
        subject_id=uuid4(),
        periods_per_week=periods_per_week,
    )


def make_assignment(
    *,
    requirement,
    teacher,
    group,
    period,
    day: DayOfWeek = DayOfWeek.MONDAY,
) -> SchedulingAssignment:
    return SchedulingAssignment(
        lesson_requirement_id=requirement.id,
        teacher_id=teacher.id,
        teaching_group_id=group.id,
        period_id=period.id,
        day=day,
        room_id=None,
    )


def make_problem(
    *,
    periods,
    teachers,
    groups,
    requirements,
    teacher_free_afternoons,
) -> SchedulingProblem:
    return SchedulingProblem.from_iterables(
        periods=periods,
        teachers=teachers,
        teaching_groups=groups,
        rooms=(),
        lesson_requirements=requirements,
        teacher_assignments=(),
        teacher_availability=(),
        teacher_free_afternoons=teacher_free_afternoons,
        room_availability=(),
        slots=(),
    )


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------


def test_validator_returns_valid_summary_for_valid_timetable():
    teacher = make_teacher()
    group = make_group()
    period = make_period()
    requirement = make_requirement(
        group_id=group.id,
    )

    free_afternoon = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
    )

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group,),
        requirements=(requirement,),
        teacher_free_afternoons=(free_afternoon,),
    )

    summary = TimetableValidator().validate(
        problem,
        (assignment,),
    )

    assert summary.is_valid is True
    assert summary.error_count == 0
    assert summary.warning_count == 0
    assert summary.total_count == 0


# ---------------------------------------------------------------------------
# Teacher clash orchestration
# ---------------------------------------------------------------------------


def test_validator_collects_teacher_clash():
    teacher = make_teacher()
    group_one = make_group()
    group_two = make_group()
    period = make_period()

    requirement_one = make_requirement(
        group_id=group_one.id,
    )

    requirement_two = make_requirement(
        group_id=group_two.id,
    )

    assignment_one = make_assignment(
        requirement=requirement_one,
        teacher=teacher,
        group=group_one,
        period=period,
    )

    assignment_two = make_assignment(
        requirement=requirement_two,
        teacher=teacher,
        group=group_two,
        period=period,
    )

    free_afternoon = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group_one, group_two),
        requirements=(requirement_one, requirement_two),
        teacher_free_afternoons=(free_afternoon,),
    )

    summary = validate_timetable(
        problem,
        (
            assignment_one,
            assignment_two,
        ),
    )

    assert summary.is_valid is False
    assert summary.error_count >= 1

    categories = {
        finding.category
        for finding in summary.findings
    }

    assert ValidationCategory.TEACHER_CLASH.value in categories


# ---------------------------------------------------------------------------
# Teaching-group clash orchestration
# ---------------------------------------------------------------------------


def test_validator_collects_teaching_group_clash():
    teacher_one = make_teacher()
    teacher_two = make_teacher()
    group = make_group()
    period = make_period()

    requirement_one = make_requirement(
        group_id=group.id,
    )

    requirement_two = make_requirement(
        group_id=group.id,
    )

    assignment_one = make_assignment(
        requirement=requirement_one,
        teacher=teacher_one,
        group=group,
        period=period,
    )

    assignment_two = make_assignment(
        requirement=requirement_two,
        teacher=teacher_two,
        group=group,
        period=period,
    )

    free_afternoon_one = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher_one.id,
        day=DayOfWeek.MONDAY,
    )

    free_afternoon_two = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher_two.id,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher_one, teacher_two),
        groups=(group,),
        requirements=(requirement_one, requirement_two),
        teacher_free_afternoons=(
            free_afternoon_one,
            free_afternoon_two,
        ),
    )

    summary = validate(
        problem,
        (
            assignment_one,
            assignment_two,
        ),
    )

    categories = {
        finding.category
        for finding in summary.findings
    }

    assert ValidationCategory.GROUP_CLASH.value in categories


# ---------------------------------------------------------------------------
# Duplicate-entry orchestration
# ---------------------------------------------------------------------------


def test_validator_collects_duplicate_entry():
    teacher = make_teacher()
    group = make_group()
    period = make_period()

    requirement = make_requirement(
        group_id=group.id,
    )

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period,
    )

    free_afternoon = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group,),
        requirements=(requirement,),
        teacher_free_afternoons=(free_afternoon,),
    )

    summary = validate_timetable(
        problem,
        (
            assignment,
            assignment,
        ),
    )

    categories = {
        finding.category
        for finding in summary.findings
    }

    assert ValidationCategory.DUPLICATE_ENTRY.value in categories
    assert summary.is_valid is False


# ---------------------------------------------------------------------------
# Free-afternoon orchestration
# ---------------------------------------------------------------------------


def test_validator_collects_free_afternoon_violation():
    teacher = make_teacher()
    group = make_group()

    afternoon_period = make_period(
        number=6,
        part_of_day=PartOfDay.AFTERNOON,
    )

    requirement = make_requirement(
        group_id=group.id,
    )

    free_afternoon = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
    )

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=afternoon_period,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(afternoon_period,),
        teachers=(teacher,),
        groups=(group,),
        requirements=(requirement,),
        teacher_free_afternoons=(free_afternoon,),
    )

    summary = validate_timetable(
        problem,
        (assignment,),
    )

    findings = [
        finding
        for finding in summary.findings
        if finding.category
        == ValidationCategory.TEACHER_FREE_AFTERNOON.value
    ]

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert summary.is_valid is False


# ---------------------------------------------------------------------------
# Lesson requirement orchestration
# ---------------------------------------------------------------------------


def test_validator_collects_lesson_requirement_shortfall():
    teacher = make_teacher()
    group = make_group()
    period = make_period()

    requirement = make_requirement(
        group_id=group.id,
        periods_per_week=2,
    )

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period,
    )

    free_afternoon = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group,),
        requirements=(requirement,),
        teacher_free_afternoons=(free_afternoon,),
    )

    summary = validate_timetable(
        problem,
        (assignment,),
    )

    categories = {
        finding.category
        for finding in summary.findings
    }

    assert ValidationCategory.LESSON_REQUIREMENT.value in categories
    assert summary.is_valid is False


# ---------------------------------------------------------------------------
# Multiple findings
# ---------------------------------------------------------------------------


def test_validator_aggregates_multiple_findings():
    teacher = make_teacher()
    group = make_group()
    period = make_period()

    requirement = make_requirement(
        group_id=group.id,
        periods_per_week=2,
    )

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period,
    )

    free_afternoon = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group,),
        requirements=(requirement,),
        teacher_free_afternoons=(free_afternoon,),
    )

    summary = validate(
        problem,
        (
            assignment,
            assignment,
        ),
    )

    categories = {
        finding.category
        for finding in summary.findings
    }

    assert summary.is_valid is False
    assert summary.error_count >= 2

    assert (
        ValidationCategory.DUPLICATE_ENTRY.value
        in categories
    )

    assert (
        ValidationCategory.LESSON_REQUIREMENT.value
        in categories
    )


# ---------------------------------------------------------------------------
# Assignment iterable handling
# ---------------------------------------------------------------------------


def test_validator_accepts_generator_assignments():
    teacher = make_teacher()
    group = make_group()
    period = make_period()

    requirement = make_requirement(
        group_id=group.id,
    )

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period,
    )

    free_afternoon = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group,),
        requirements=(requirement,),
        teacher_free_afternoons=(free_afternoon,),
    )

    assignments = (
        assignment
        for assignment in (assignment,)
    )

    summary = validate_timetable(
        problem,
        assignments,
    )

    assert summary.is_valid is True
    assert summary.total_count == 0