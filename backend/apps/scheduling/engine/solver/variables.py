from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ortools.sat.python import cp_model


@dataclass(frozen=True, slots=True)
class AssignmentVariable:
    """
    CP-SAT Boolean variable representing one possible lesson placement.

    The variable is true when the lesson requirement occupies the
    specified group, room and timetable slot. teacher_id may be None
    when teacher assignment is intentionally deferred.
    """

    lesson_requirement_id: UUID
    teacher_id: UUID | None
    instructional_group_id: UUID
    period_id: UUID
    day: str
    room_id: UUID | None
    variable: cp_model.IntVar
