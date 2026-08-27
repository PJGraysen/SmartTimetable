from __future__ import annotations

from typing import Iterable

from apps.academics.models import (
    InstructionalGroup,
    LessonRequirement,
    TeachingGroup,
)

from apps.scheduling.models import (
    Period,
    Room,
    RoomAvailability,
    TeacherAssignment,
    TeacherAvailability,
    TeacherFreeAfternoon,
)

from apps.users.models import Teacher

from apps.scheduling.engine.domain.entities import (
    InstructionalGroupEntity,
    LessonRequirementEntity,
    PeriodEntity,
    RoomAvailabilityEntity,
    RoomEntity,
    TeacherAssignmentEntity,
    TeacherAvailabilityEntity,
    TeacherEntity,
    TeacherFreeAfternoonEntity,
    TimetableSlot,
)

from apps.scheduling.engine.domain.enums import DayOfWeek

from apps.scheduling.engine.domain.problem import (
    SchedulingProblem,
)


class DjangoSchedulingLoader:
    """
    Converts Django scheduling records into the scheduling-engine domain model.

    Django ORM objects remain inside this infrastructure boundary.
    The solver receives only domain entities.
    """

    def load_problem(self, *, term) -> SchedulingProblem:
        teaching_groups = (
            TeachingGroup.objects
            .filter(
                stream__grade__academic_year=term.academic_year,
                is_active=True,
            )
            .select_related(
                "stream",
                "stream__grade",
            )
        )

        instructional_groups = (
            InstructionalGroup.objects
            .filter(
                teaching_group__stream__grade__academic_year=term.academic_year,
                is_active=True,
            )
            .select_related(
                "teaching_group",
                "teaching_group__stream",
                "teaching_group__stream__grade",
            )
        )

        lesson_requirements = (
            LessonRequirement.objects
            .filter(
                term=term,
                is_active=True,
            )
            .select_related(
                "instructional_group",
                "instructional_group__teaching_group",
                "subject",
            )
        )

        teachers = Teacher.objects.filter(
            is_active=True,
        )

        teacher_assignments = (
            TeacherAssignment.objects
            .filter(
                lesson_requirement__term=term,
                is_active=True,
                teacher__is_active=True,
                lesson_requirement__is_active=True,
            )
            .select_related(
                "teacher",
                "lesson_requirement",
            )
        )

        teacher_free_afternoons = (
            TeacherFreeAfternoon.objects
            .filter(
                term=term,
                is_active=True,
                teacher__is_active=True,
            )
            .select_related("teacher")
        )

        teacher_availability = (
            TeacherAvailability.objects
            .filter(
                term=term,
                is_active=True,
                teacher__is_active=True,
            )
            .select_related(
                "teacher",
                "period",
            )
        )

        rooms = Room.objects.filter(
            is_active=True,
        )

        periods = (
            Period.objects
            .filter(is_active=True)
            .order_by("number", "id")
        )

        room_availability = (
            RoomAvailability.objects
            .filter(
                term=term,
                is_active=True,
                room__is_active=True,
                period__is_active=True,
            )
            .select_related(
                "room",
                "period",
            )
        )

        loaded_periods = tuple(load_periods(periods))

        slots = build_timetable_slots(
            loaded_periods,
        )

        return SchedulingProblem(
            periods=loaded_periods,
            teachers=tuple(
                load_teachers(teachers)
            ),
            instructional_groups=tuple(
                load_instructional_groups(
                    instructional_groups
                )
            ),
            rooms=tuple(
                load_rooms(rooms)
            ),
            lesson_requirements=tuple(
                load_lesson_requirements(
                    lesson_requirements
                )
            ),
            teacher_assignments=tuple(
                load_teacher_assignments(
                    teacher_assignments
                )
            ),
            teacher_availability=tuple(
                load_teacher_availability(
                    teacher_availability
                )
            ),
            teacher_free_afternoons=tuple(
                load_teacher_free_afternoons(
                    teacher_free_afternoons
                )
            ),
            room_availability=tuple(
                load_room_availability(
                    room_availability
                )
            ),
            slots=slots,
        )


def load_periods(
    periods: Iterable[Period],
) -> list[PeriodEntity]:
    return [
        PeriodEntity(
            id=period.id,
            number=period.number,
            name=period.name,
            start_time=period.start_time,
            end_time=period.end_time,
            part_of_day=period.part_of_day,
            is_teaching_period=period.is_teaching_period,
            is_active=period.is_active,
        )
        for period in periods
    ]


def load_teachers(
    teachers: Iterable[Teacher],
) -> list[TeacherEntity]:
    result: list[TeacherEntity] = []

    for teacher in teachers:
        get_full_name = getattr(teacher, "get_full_name", None)

        if callable(get_full_name):
            name = get_full_name().strip()
        else:
            first_name = str(
                getattr(teacher, "first_name", "") or ""
            ).strip()

            last_name = str(
                getattr(teacher, "last_name", "") or ""
            ).strip()

            name = " ".join(
                part
                for part in (first_name, last_name)
                if part
            ).strip()

        if not name:
            name = str(teacher).strip()

        result.append(
            TeacherEntity(
                id=teacher.id,
                name=name,
                code=teacher.employee_code,
                is_active=teacher.is_active,
            )
        )

    return result


def load_instructional_groups(
    groups: Iterable[InstructionalGroup],
) -> list[InstructionalGroupEntity]:
    result: list[InstructionalGroupEntity] = []

    for group in groups:
        teaching_group = getattr(
            group,
            "teaching_group",
            None,
        )

        if teaching_group is not None:
            entity_id = group.id
            code = group.code
            is_active = group.is_active

            name = str(teaching_group)
        else:
            entity_id = group.id
            code = group.code
            is_active = group.is_active
            name = str(group)

        result.append(
            InstructionalGroupEntity(
                id=entity_id,
                name=name,
                code=code,
                is_active=is_active,
            )
        )

    return result


def load_rooms(
    rooms: Iterable[Room],
) -> list[RoomEntity]:
    return [
        RoomEntity(
            id=room.id,
            name=room.name,
            code=room.code,
            capacity=room.capacity,
            is_active=room.is_active,
        )
        for room in rooms
    ]


def load_lesson_requirements(
    requirements: Iterable[LessonRequirement],
) -> list[LessonRequirementEntity]:
    result: list[LessonRequirementEntity] = []

    for requirement in requirements:
        subject = requirement.subject

        result.append(
            LessonRequirementEntity(
                id=requirement.id,
                instructional_group_id=(
                    requirement.instructional_group_id
                ),
                subject_id=requirement.subject_id,
                periods_per_week=requirement.lessons_per_week,
                is_active=requirement.is_active,
                subject_code=(
                    str(subject.code)
                    if subject is not None
                    else ""
                ),
            )
        )

    return result


def load_teacher_assignments(
    assignments: Iterable[TeacherAssignment],
) -> list[TeacherAssignmentEntity]:
    return [
        TeacherAssignmentEntity(
            id=assignment.id,
            teacher_id=assignment.teacher_id,
            lesson_requirement_id=(
                assignment.lesson_requirement_id
            ),
            is_active=assignment.is_active,
        )
        for assignment in assignments
    ]


def _coerce_day(value) -> DayOfWeek:
    """
    Convert Django day values into the domain DayOfWeek enum.

    Django fixtures/tests may provide either an existing DayOfWeek
    instance or its stored string value such as MON/TUE/WED/THU/FRI.
    """
    if isinstance(value, DayOfWeek):
        return value

    raw = str(value).strip()

    try:
        return DayOfWeek(raw)
    except ValueError:
        pass

    raw_upper = raw.upper()

    aliases = {
        "MONDAY": "MON",
        "TUESDAY": "TUE",
        "WEDNESDAY": "WED",
        "THURSDAY": "THU",
        "FRIDAY": "FRI",
    }

    raw_upper = aliases.get(raw_upper, raw_upper)

    try:
        return DayOfWeek(raw_upper)
    except ValueError:
        pass

    for member in DayOfWeek:
        if str(member.name).upper() == raw_upper:
            return member

    raise ValueError(
        f"Unsupported DayOfWeek value: {value!r}"
    )


def load_teacher_free_afternoons(
    entries: Iterable[TeacherFreeAfternoon],
) -> list[TeacherFreeAfternoonEntity]:
    return [
        TeacherFreeAfternoonEntity(
            id=entry.id,
            teacher_id=entry.teacher_id,
            day=_coerce_day(entry.day),
            is_active=entry.is_active,
        )
        for entry in entries
    ]


def load_teacher_availability(
    entries: Iterable[TeacherAvailability],
) -> list[TeacherAvailabilityEntity]:
    return [
        TeacherAvailabilityEntity(
            id=entry.id,
            teacher_id=entry.teacher_id,
            day=_coerce_day(entry.day),
            period_id=entry.period_id,
            is_available=entry.is_available,
            is_active=entry.is_active,
        )
        for entry in entries
    ]


def load_room_availability(
    entries: Iterable[RoomAvailability],
) -> list[RoomAvailabilityEntity]:
    return [
        RoomAvailabilityEntity(
            id=entry.id,
            room_id=entry.room_id,
            day=_coerce_day(entry.day),
            period_id=entry.period_id,
            is_available=entry.is_available,
            is_active=entry.is_active,
        )
        for entry in entries
    ]


def _resolve_weekdays() -> tuple[DayOfWeek, ...]:
    """
    Resolve Monday-Friday without assuming that the enum members
    are named MON/TUE/WED/THU/FRI.

    The actual domain enum has already been established as DayOfWeek,
    but its member names are intentionally resolved from the enum
    itself rather than guessed.
    """

    members = list(DayOfWeek)

    if len(members) < 5:
        raise RuntimeError(
            "DayOfWeek contains fewer than five members; "
            "cannot construct the Monday-Friday timetable slot universe."
        )

    aliases = {
        "monday": 0,
        "mon": 0,
        "tuesday": 1,
        "tue": 1,
        "tues": 1,
        "wednesday": 2,
        "wed": 2,
        "thursday": 3,
        "thu": 3,
        "thur": 3,
        "thurs": 3,
        "friday": 4,
        "fri": 4,
    }

    resolved: dict[int, DayOfWeek] = {}

    for member in members:
        candidates = (
            str(getattr(member, "name", "")).lower(),
            str(getattr(member, "value", "")).lower(),
        )

        for candidate in candidates:
            candidate = candidate.strip()

            if candidate in aliases:
                resolved.setdefault(
                    aliases[candidate],
                    member,
                )

    if len(resolved) == 5:
        return tuple(
            resolved[index]
            for index in range(5)
        )

    # If names/values are not textual weekday names, preserve the
    # enum's declared order, which is the domain's canonical order.
    return tuple(members[:5])


def build_timetable_slots(
    periods: Iterable[PeriodEntity],
) -> tuple[TimetableSlot, ...]:
    """
    Build the complete Monday-Friday × active-period slot universe.

    Period numbers and part-of-day values come directly from the
    loaded PeriodEntity records. No period numbers are hard-coded.
    """

    loaded_periods = tuple(periods)
    weekdays = _resolve_weekdays()

    slots: list[TimetableSlot] = []

    for day in weekdays:
        for period in loaded_periods:
            slots.append(
                TimetableSlot(
                    day=day,
                    period_id=period.id,
                    period_number=period.number,
                    part_of_day=period.part_of_day,
                )
            )

    return tuple(slots)
