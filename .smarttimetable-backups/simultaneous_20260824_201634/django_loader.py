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
    InstructionalGroupEntity,
    TimetableSlot,
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
from apps.academics.models import InstructionalGroup, LessonRequirement
from apps.users.models import Teacher
from apps.scheduling.engine.domain.problem import SchedulingProblem


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
            code=teacher.employee_code,
            is_active=teacher.is_active,
        )
        for teacher in queryset
    ]


def load_instructional_groups(
    queryset: Iterable[InstructionalGroup],
) -> list[InstructionalGroupEntity]:
    """Convert Django InstructionalGroup records into domain entities."""

    return [
        InstructionalGroupEntity(
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
            instructional_group_id=requirement.instructional_group_id,
            subject_id=requirement.subject_id,
            subject_code=(
                getattr(getattr(requirement, "subject", None), "code", None)
                or getattr(getattr(requirement, "subject", None), "name", "")
                or ""
            ),
            periods_per_week=requirement.lessons_per_week,
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
def load_slots(
    periods: Iterable[Period],
) -> list[TimetableSlot]:
    """
    Generate concrete Monday-Friday timetable slots from active periods.

    Every active period becomes one slot for each school day.
    Non-teaching periods are retained because they are part of the
    timetable structure, while the solver itself decides which slots
    are eligible for lesson assignment.
    """

    slots: list[TimetableSlot] = []

    days = (
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    )

    for period in periods:
        if not period.is_active:
            continue

        for day in days:
            slots.append(
                TimetableSlot(
                    day=day,
                    period_id=period.id,
                    period_number=period.number,
                    part_of_day=PartOfDay(period.part_of_day),
                )
            )

    return slots

def load_scheduling_problem(term) -> "SchedulingProblem":
    """
    Load all scheduling inputs for a specific academic term and convert
    them into an immutable SchedulingProblem.

    Django remains confined to this infrastructure layer. The returned
    domain object contains no Django model instances.
    """

    from apps.scheduling.engine.domain.problem import SchedulingProblem

    periods_queryset = Period.objects.filter(
        is_active=True,
    ).order_by("number")

    teachers_queryset = Teacher.objects.filter(
        is_active=True,
    ).order_by("employee_code")

    instructional_groups_queryset = InstructionalGroup.objects.filter(
        is_active=True,
    )

    rooms_queryset = Room.objects.filter(
        is_active=True,
    )

    lesson_requirements_queryset = LessonRequirement.objects.filter(
        term=term,
        is_active=True,
    ).order_by("instructional_group", "subject")

    teacher_assignments_queryset = TeacherAssignment.objects.filter(
        is_active=True,
        lesson_requirement__term=term,
    ).order_by("teacher", "lesson_requirement")

    teacher_availability_queryset = TeacherAvailability.objects.filter(
        term=term,
        is_active=True,
    ).order_by("teacher", "day", "period__number")

    teacher_free_afternoons_queryset = TeacherFreeAfternoon.objects.filter(
        term=term,
        is_active=True,
    ).order_by("teacher", "day")

    room_availability_queryset = RoomAvailability.objects.filter(
        term=term,
        is_active=True,
    ).order_by("room", "day", "period__number")

    periods = load_periods(periods_queryset)

    teachers = load_teachers(teachers_queryset)

    instructional_groups = load_instructional_groups(instructional_groups_queryset)

    rooms = load_rooms(rooms_queryset)

    lesson_requirements = load_lesson_requirements(lesson_requirements_queryset)

    teacher_assignments = load_teacher_assignments(teacher_assignments_queryset)

    teacher_availability = load_teacher_availability(teacher_availability_queryset)

    teacher_free_afternoons = load_teacher_free_afternoons(teacher_free_afternoons_queryset)

    room_availability = load_room_availability(room_availability_queryset)

    slots = load_slots(periods_queryset)

    return SchedulingProblem.from_iterables(
        periods=periods,
        teachers=teachers,
        instructional_groups=instructional_groups,
        rooms=rooms,
        lesson_requirements=lesson_requirements,
        teacher_assignments=teacher_assignments,
        teacher_availability=teacher_availability,
        teacher_free_afternoons=teacher_free_afternoons,
        room_availability=room_availability,
        slots=slots,
    )
class DjangoSchedulingLoader:
    """Infrastructure adapter for loading scheduling problems from Django."""

    def load_problem(self, *, term) -> SchedulingProblem:
        return load_scheduling_problem(term)

