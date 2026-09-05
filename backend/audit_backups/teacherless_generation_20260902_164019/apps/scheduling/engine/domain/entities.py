from dataclasses import dataclass
from datetime import time
from typing import Optional
from uuid import UUID

from .enums import DayOfWeek, PartOfDay


@dataclass(frozen=True, slots=True)
class PeriodEntity:
    """A single timetable period."""

    id: UUID
    number: int
    name: str
    start_time: time
    end_time: time
    part_of_day: PartOfDay
    is_teaching_period: bool
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class TeacherEntity:
    """A teacher participating in timetable generation."""

    id: UUID
    name: str
    code: str
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class InstructionalGroupEntity:
    """A class or teaching group that receives lessons."""

    id: UUID
    name: str
    code: str
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class RoomEntity:
    """A physical room that can host a lesson."""

    id: UUID
    name: str
    code: str
    capacity: int
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class LessonRequirementEntity:
    """
    A requirement describing how much teaching a group/subject
    combination requires.
    """

    id: UUID
    instructional_group_id: UUID
    subject_id: UUID
    periods_per_week: int
    subject_code: str | None = None
    is_active: bool = True
@dataclass(frozen=True, slots=True)
class TeacherAssignmentEntity:
    """Assignment of a teacher to a lesson requirement."""

    id: UUID
    teacher_id: UUID
    lesson_requirement_id: UUID
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class TeacherAvailabilityEntity:
    """
    Teacher availability for a specific term/day/period.

    is_available=False represents a hard unavailable slot.
    """

    id: UUID
    teacher_id: UUID
    day: DayOfWeek
    period_id: UUID
    is_available: bool
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class TeacherFreeAfternoonEntity:
    """
    The teacher's designated weekly free afternoon.

    This is a hard constraint: the teacher must not receive
    any teaching period belonging to this afternoon on the
    designated day.
    """

    id: UUID
    teacher_id: UUID
    day: DayOfWeek
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class RoomAvailabilityEntity:
    """Room availability for a specific term/day/period."""

    id: UUID
    room_id: UUID
    day: DayOfWeek
    period_id: UUID
    is_available: bool
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class TimetableSlot:
    """A concrete day/period combination."""

    day: DayOfWeek
    period_id: UUID
    period_number: int
    part_of_day: PartOfDay


@dataclass(frozen=True, slots=True)
class SchedulingAssignment:
    """
    A solver-level assignment of a lesson requirement
    to a teacher, group, room and timetable slot.
    """

    lesson_requirement_id: UUID
    teacher_id: UUID
    instructional_group_id: UUID
    period_id: UUID
    day: DayOfWeek
    room_id: Optional[UUID] = None


