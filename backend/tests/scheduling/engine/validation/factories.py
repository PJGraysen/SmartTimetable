from __future__ import annotations

from datetime import time
from uuid import uuid4

from apps.scheduling.engine.domain.entities import (
    LessonRequirementEntity,
    PeriodEntity,
    RoomAvailabilityEntity,
    RoomEntity,
    SchedulingAssignment,
    TeacherAvailabilityEntity,
    TeacherEntity,
    TeacherFreeAfternoonEntity,
    TeachingGroupEntity,
)
from apps.scheduling.engine.domain.enums import (
    DayOfWeek,
    PartOfDay,
)
from apps.scheduling.engine.domain.problem import SchedulingProblem


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


def make_room() -> RoomEntity:
    return RoomEntity(
        id=uuid4(),
        name="Room 1",
        code="R1",
        capacity=50,
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
    room=None,
) -> SchedulingAssignment:
    return SchedulingAssignment(
        lesson_requirement_id=requirement.id,
        teacher_id=teacher.id,
        teaching_group_id=group.id,
        period_id=period.id,
        day=day,
        room_id=room.id if room else None,
    )


def make_problem(
    *,
    periods,
    teachers,
    groups,
    rooms=(),
    requirements,
    teacher_assignments=(),
    teacher_availability=(),
    teacher_free_afternoons=None,
    room_availability=(),
    slots=(),
) -> SchedulingProblem:
    """
    Build a valid SchedulingProblem fixture.

    Every active teacher must have exactly one active free-afternoon
    assignment. When no explicit free-afternoon collection is supplied,
    give each active teacher a valid default assignment.

    Passing an explicit value, including an empty tuple, preserves the
    caller's intent.
    """
    if teacher_free_afternoons is None:
        teacher_free_afternoons = tuple(
            TeacherFreeAfternoonEntity(
                id=uuid4(),
                teacher_id=teacher.id,
                day=DayOfWeek.FRIDAY,
            )
            for teacher in teachers
            if teacher.is_active
        )

    return SchedulingProblem.from_iterables(
        periods=periods,
        teachers=teachers,
        teaching_groups=groups,
        rooms=rooms,
        lesson_requirements=requirements,
        teacher_assignments=teacher_assignments,
        teacher_availability=teacher_availability,
        teacher_free_afternoons=teacher_free_afternoons,
        room_availability=room_availability,
        slots=slots,
    )
