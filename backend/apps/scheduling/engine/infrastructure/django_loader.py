from __future__ import annotations

from typing import Iterable
from uuid import UUID

from apps.scheduling.engine.domain.entities import (
    LessonRequirementEntity,
    PeriodEntity,
    RoomAvailabilityEntity,
    RoomEntity,
    TeacherAssignmentEntity,
    TeacherAvailabilityEntity,
    TeacherEntity,
    TeacherFreeAfternoonEntity,
    TeachingGroupEntity,
)
from apps.scheduling.engine.domain.enums import (
    DayOfWeek,
    PartOfDay,
)
from apps.scheduling.models import (
    Period,
    Room,
    RoomAvailability,
    TeacherAssignment,
    TeacherAvailability,
    TeacherFreeAfternoon,
)
from apps.academics.models import LessonRequirement, TeachingGroup
from apps.users.models import Teacher


def load_periods(
    queryset: Iterable[Period],
) -> list[PeriodEntity]:
    """Convert Django Period records into domain entities."""

    return [
        PeriodEntity(
            id=period.id,
            number=period.number,
            name=period.name,
            start_time=period.start_time,
            end_time=period.end_time,
            part_of_day=PartOfDay(period.part_of_day),
            is_teaching_period=period.is_teaching_period,
            is_active=period.is_active,
        )
        for period in queryset
    ]


def load_teachers(
    queryset: Iterable[Teacher],
) -> list[TeacherEntity]:
    """Convert Django Teacher records into domain entities."""

    return [
        TeacherEntity(
            id=teacher.id,
            name=str(teacher),
            code=getattr(teacher, "code", str(teacher.id)),
            is_active=teacher.is_active,
        )
        for teacher in queryset
    ]


def load_teaching_groups(
    queryset: Iterable[TeachingGroup],
) -> list[TeachingGroupEntity]:
    """Convert Django TeachingGroup records into domain entities."""

    return [
        TeachingGroupEntity(
            id=group.id,
            name=str(group),
            code=getattr(group, "code", str(group.id)),
            is_active=group.is_active,
        )
        for group in queryset
    ]


def load_rooms(
    queryset: Iterable[Room],
) -> list[RoomEntity]:
    """Convert Django Room records into domain entities."""

    return [
        RoomEntity(
            id=room.id,
            name=room.name,
            code=room.code,
            capacity=room.capacity,
            is_active=room.is_active,
        )
        for room in queryset
    ]


def load_lesson_requirements(
    queryset: Iterable[LessonRequirement],
) -> list[LessonRequirementEntity]:
    """Convert Django lesson requirements into domain entities."""

    return [
        LessonRequirementEntity(
            id=requirement.id,
            teaching_group_id=requirement.teaching_group_id,
            subject_id=requirement.subject_id,
            periods_per_week=requirement.periods_per_week,
            is_active=requirement.is_active,
        )
        for requirement in queryset
    ]


def load_teacher_assignments(
    queryset: Iterable[TeacherAssignment],
) -> list[TeacherAssignmentEntity]:
    """Convert teacher assignments into domain entities."""

    return [
        TeacherAssignmentEntity(
            id=assignment.id,
            teacher_id=assignment.teacher_id,
            lesson_requirement_id=assignment.lesson_requirement_id,
            is_active=assignment.is_active,
        )
        for assignment in queryset
    ]


def load_teacher_availability(
    queryset: Iterable[TeacherAvailability],
) -> list[TeacherAvailabilityEntity]:
    """Convert teacher availability records into domain entities."""

    return [
        TeacherAvailabilityEntity(
            id=availability.id,
            teacher_id=availability.teacher_id,
            day=DayOfWeek(availability.day),
            period_id=availability.period_id,
            is_available=availability.is_available,
            is_active=availability.is_active,
        )
        for availability in queryset
    ]


def load_teacher_free_afternoons(
    queryset: Iterable[TeacherFreeAfternoon],
) -> list[TeacherFreeAfternoonEntity]:
    """
    Convert mandatory teacher free-afternoon records.

    The resulting domain objects represent a HARD scheduling constraint.
    """

    return [
        TeacherFreeAfternoonEntity(
            id=free_afternoon.id,
            teacher_id=free_afternoon.teacher_id,
            day=DayOfWeek(free_afternoon.day),
            is_active=free_afternoon.is_active,
        )
        for free_afternoon in queryset
    ]


def load_room_availability(
    queryset: Iterable[RoomAvailability],
) -> list[RoomAvailabilityEntity]:
    """Convert room availability records into domain entities."""

    return [
        RoomAvailabilityEntity(
            id=availability.id,
            room_id=availability.room_id,
            day=DayOfWeek(availability.day),
            period_id=availability.period_id,
            is_available=availability.is_available,
            is_active=availability.is_active,
        )
        for availability in queryset
    ]