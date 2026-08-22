from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ortools.sat.python import cp_model


@dataclass(frozen=True, slots=True)
class AssignmentVariable:
    """
    CP-SAT Boolean variable representing one possible lesson placement.

    The variable is true when the lesson requirement is assigned to the
    specified teacher, group, room and timetable slot.
    """

    lesson_requirement_id: UUID
    teacher_id: UUID
    instructional_group_id: UUID
    period_id: UUID
    day: str
    room_id: UUID | None
    variable: cp_model.IntVar
