from dataclasses import dataclass, field
from typing import Iterable, Mapping
from uuid import UUID

from .entities import (
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
from .enums import DayOfWeek, PartOfDay


@dataclass(frozen=True, slots=True)
class SchedulingProblem:
    """
    Complete domain representation of a timetable scheduling problem.

    This class is intentionally independent of Django and OR-Tools.
    It represents the scheduling inputs that will later be translated
    into a solver model.
    """

    periods: tuple[PeriodEntity, ...]
    teachers: tuple[TeacherEntity, ...]
    instructional_groups: tuple[InstructionalGroupEntity, ...]
    rooms: tuple[RoomEntity, ...]
    lesson_requirements: tuple[LessonRequirementEntity, ...]
    teacher_assignments: tuple[TeacherAssignmentEntity, ...]
    teacher_availability: tuple[TeacherAvailabilityEntity, ...]
    teacher_free_afternoons: tuple[TeacherFreeAfternoonEntity, ...]
    room_availability: tuple[RoomAvailabilityEntity, ...]
    slots: tuple[TimetableSlot, ...]

    def __post_init__(self) -> None:
        """Validate the structural integrity of the scheduling problem."""

        self._validate_unique_ids()
        self._validate_references()
        self._validate_periods()
        self._validate_lesson_requirements()
        self._validate_teacher_assignments()
        self._validate_teacher_availability()
        self._validate_teacher_free_afternoons()
        self._validate_room_availability()
        self._validate_slots()

    # ------------------------------------------------------------------
    # Public lookup helpers
    # ------------------------------------------------------------------

    @property
    def active_periods(self) -> tuple[PeriodEntity, ...]:
        """Return active timetable periods."""
        return tuple(period for period in self.periods if period.is_active)

    @property
    def teaching_periods(self) -> tuple[PeriodEntity, ...]:
        """Return active periods during which teaching can occur."""
        return tuple(
            period
            for period in self.periods
            if period.is_active and period.is_teaching_period
        )

    @property
    def afternoon_teaching_periods(self) -> tuple[PeriodEntity, ...]:
        """Return active teaching periods belonging to the afternoon."""
        return tuple(
            period
            for period in self.periods
            if (
                period.is_active
                and period.is_teaching_period
                and period.part_of_day == PartOfDay.AFTERNOON
            )
        )

    @property
    def teacher_by_id(self) -> Mapping[UUID, TeacherEntity]:
        """Map teacher IDs to teacher entities."""
        return {teacher.id: teacher for teacher in self.teachers}

    @property
    def period_by_id(self) -> Mapping[UUID, PeriodEntity]:
        """Map period IDs to period entities."""
        return {period.id: period for period in self.periods}

    @property
    def instructional_group_by_id(self) -> Mapping[UUID, InstructionalGroupEntity]:
        """Map instructional-group IDs to instructional-group entities."""
        return {
            instructional_group.id: instructional_group
            for instructional_group in self.instructional_groups
        }

    @property
    def room_by_id(self) -> Mapping[UUID, RoomEntity]:
        """Map room IDs to room entities."""
        return {room.id: room for room in self.rooms}

    @property
    def lesson_requirement_by_id(
        self,
    ) -> Mapping[UUID, LessonRequirementEntity]:
        """Map lesson requirement IDs to lesson requirements."""
        return {
            requirement.id: requirement
            for requirement in self.lesson_requirements
        }

    def teacher_free_afternoon(
        self,
        teacher_id: UUID,
    ) -> TeacherFreeAfternoonEntity | None:
        """
        Return the teacher's designated weekly free afternoon.

        Each active teacher must have exactly one active free-afternoon
        assignment. Structural validation guarantees that there is at
        most one.
        """
        matches = tuple(
            assignment
            for assignment in self.teacher_free_afternoons
            if assignment.teacher_id == teacher_id
            and assignment.is_active
        )

        if not matches:
            return None

        return matches[0]

    def is_teacher_free_afternoon(
        self,
        teacher_id: UUID,
        day: DayOfWeek,
        period_id: UUID,
    ) -> bool:
        """
        Determine whether a teacher is prohibited from teaching in a slot.

        A teacher's designated free afternoon blocks every active
        afternoon teaching period on that day.
        """
        assignment = self.teacher_free_afternoon(teacher_id)

        if assignment is None:
            return False

        if assignment.day != day:
            return False

        period = self.period_by_id.get(period_id)

        if period is None:
            return False

        return (
            period.is_active
            and period.is_teaching_period
            and period.part_of_day == PartOfDay.AFTERNOON
        )

    # ------------------------------------------------------------------
    # Structural validation
    # ------------------------------------------------------------------

    def _validate_unique_ids(self) -> None:
        """Ensure every entity collection contains unique IDs."""

        collections = (
            ("period", self.periods),
            ("teacher", self.teachers),
            ("instructional group", self.instructional_groups),
            ("room", self.rooms),
            ("lesson requirement", self.lesson_requirements),
            ("teacher assignment", self.teacher_assignments),
            ("teacher availability", self.teacher_availability),
            ("teacher free afternoon", self.teacher_free_afternoons),
            ("room availability", self.room_availability),
        )

        for name, entities in collections:
            ids = [entity.id for entity in entities]

            if len(ids) != len(set(ids)):
                raise ValueError(
                    f"Duplicate {name} IDs detected."
                )

    def _validate_references(self) -> None:
        """Ensure foreign-key-like domain references point to known entities."""

        period_ids = {period.id for period in self.periods}
        teacher_ids = {teacher.id for teacher in self.teachers}
        group_ids = {
            instructional_group.id for instructional_group in self.instructional_groups
        }
        room_ids = {room.id for room in self.rooms}
        requirement_ids = {
            requirement.id for requirement in self.lesson_requirements
        }

        for requirement in self.lesson_requirements:
            if requirement.instructional_group_id not in group_ids:
                raise ValueError(
                    "Lesson requirement "
                    f"{requirement.id} references unknown instructional group "
                    f"{requirement.instructional_group_id}."
                )

        for assignment in self.teacher_assignments:
            if assignment.teacher_id not in teacher_ids:
                raise ValueError(
                    "Teacher assignment "
                    f"{assignment.id} references unknown teacher "
                    f"{assignment.teacher_id}."
                )

            if assignment.lesson_requirement_id not in requirement_ids:
                raise ValueError(
                    "Teacher assignment "
                    f"{assignment.id} references unknown lesson requirement "
                    f"{assignment.lesson_requirement_id}."
                )

        for availability in self.teacher_availability:
            if availability.teacher_id not in teacher_ids:
                raise ValueError(
                    "Teacher availability "
                    f"{availability.id} references unknown teacher "
                    f"{availability.teacher_id}."
                )

            if availability.period_id not in period_ids:
                raise ValueError(
                    "Teacher availability "
                    f"{availability.id} references unknown period "
                    f"{availability.period_id}."
                )

        for free_afternoon in self.teacher_free_afternoons:
            if free_afternoon.teacher_id not in teacher_ids:
                raise ValueError(
                    "Teacher free-afternoon assignment "
                    f"{free_afternoon.id} references unknown teacher "
                    f"{free_afternoon.teacher_id}."
                )

        for availability in self.room_availability:
            if availability.room_id not in room_ids:
                raise ValueError(
                    "Room availability "
                    f"{availability.id} references unknown room "
                    f"{availability.room_id}."
                )

            if availability.period_id not in period_ids:
                raise ValueError(
                    "Room availability "
                    f"{availability.id} references unknown period "
                    f"{availability.period_id}."
                )

    def _validate_periods(self) -> None:
        """Validate timetable period definitions."""

        numbers = [period.number for period in self.periods]

        if len(numbers) != len(set(numbers)):
            raise ValueError(
                "Duplicate period numbers detected."
            )

        for period in self.periods:
            if period.end_time <= period.start_time:
                raise ValueError(
                    f"Period '{period.name}' has an invalid time range."
                )

            if period.number < 0:
                raise ValueError(
                    f"Period '{period.name}' has an invalid number."
                )

    def _validate_lesson_requirements(self) -> None:
        """Validate weekly teaching requirements."""

        for requirement in self.lesson_requirements:
            if requirement.periods_per_week < 0:
                raise ValueError(
                    f"Lesson requirement {requirement.id} has a negative "
                    "periods_per_week value."
                )

    def _validate_teacher_assignments(self) -> None:
        """Validate teacher-to-requirement assignments."""

        active_pairs: set[tuple[UUID, UUID]] = set()

        for assignment in self.teacher_assignments:
            if not assignment.is_active:
                continue

            pair = (
                assignment.teacher_id,
                assignment.lesson_requirement_id,
            )

            if pair in active_pairs:
                raise ValueError(
                    "Duplicate active teacher assignment detected for "
                    f"teacher {assignment.teacher_id} and lesson "
                    f"requirement {assignment.lesson_requirement_id}."
                )

            active_pairs.add(pair)

    def _validate_teacher_availability(self) -> None:
        """Validate teacher availability records."""

        active_slots: set[tuple[UUID, DayOfWeek, UUID]] = set()

        for availability in self.teacher_availability:
            if not availability.is_active:
                continue

            key = (
                availability.teacher_id,
                availability.day,
                availability.period_id,
            )

            if key in active_slots:
                raise ValueError(
                    "Duplicate active teacher availability detected for "
                    f"teacher {availability.teacher_id}, "
                    f"day {availability.day}, "
                    f"period {availability.period_id}."
                )

            active_slots.add(key)

    def _validate_teacher_free_afternoons(self) -> None:
        """
        Validate the hard weekly free-afternoon requirement.

        Every active teacher must have exactly one active free afternoon.
        """
        active_teachers = {
            teacher.id
            for teacher in self.teachers
            if teacher.is_active
        }

        assignments_by_teacher: dict[
            UUID, list[TeacherFreeAfternoonEntity]
        ] = {
            teacher_id: []
            for teacher_id in active_teachers
        }

        for assignment in self.teacher_free_afternoons:
            if not assignment.is_active:
                continue

            if assignment.teacher_id not in active_teachers:
                raise ValueError(
                    "Free-afternoon assignment "
                    f"{assignment.id} belongs to an inactive or unknown "
                    f"teacher {assignment.teacher_id}."
                )

            assignments_by_teacher[assignment.teacher_id].append(
                assignment
            )

        for teacher_id in active_teachers:
            assignments = assignments_by_teacher[teacher_id]

            if len(assignments) != 1:
                raise ValueError(
                    f"Teacher {teacher_id} must have exactly one active "
                    "free-afternoon assignment; found "
                    f"{len(assignments)}."
                )

    def _validate_room_availability(self) -> None:
        """Validate room availability records."""

        active_slots: set[tuple[UUID, DayOfWeek, UUID]] = set()

        for availability in self.room_availability:
            if not availability.is_active:
                continue

            key = (
                availability.room_id,
                availability.day,
                availability.period_id,
            )

            if key in active_slots:
                raise ValueError(
                    "Duplicate active room availability detected for "
                    f"room {availability.room_id}, "
                    f"day {availability.day}, "
                    f"period {availability.period_id}."
                )

            active_slots.add(key)

    def _validate_slots(self) -> None:
        """Validate concrete timetable slots."""

        period_ids = {period.id for period in self.periods}
        seen_slots: set[tuple[DayOfWeek, UUID]] = set()

        for slot in self.slots:
            if slot.period_id not in period_ids:
                raise ValueError(
                    f"Timetable slot references unknown period "
                    f"{slot.period_id}."
                )

            key = (slot.day, slot.period_id)

            if key in seen_slots:
                raise ValueError(
                    f"Duplicate timetable slot detected: "
                    f"{slot.day}/{slot.period_id}."
                )

            seen_slots.add(key)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_iterables(
        cls,
        *,
        periods: Iterable[PeriodEntity],
        teachers: Iterable[TeacherEntity],
        instructional_groups: Iterable[InstructionalGroupEntity],
        rooms: Iterable[RoomEntity],
        lesson_requirements: Iterable[LessonRequirementEntity],
        teacher_assignments: Iterable[TeacherAssignmentEntity],
        teacher_availability: Iterable[TeacherAvailabilityEntity],
        teacher_free_afternoons: Iterable[TeacherFreeAfternoonEntity],
        room_availability: Iterable[RoomAvailabilityEntity],
        slots: Iterable[TimetableSlot],
    ) -> "SchedulingProblem":
        """
        Construct an immutable scheduling problem from arbitrary iterables.

        Lists, querysets converted to iterables, generators and tuples can
        all be supplied. The resulting problem stores immutable tuples.
        """
        return cls(
            periods=tuple(periods),
            teachers=tuple(teachers),
            instructional_groups=tuple(instructional_groups),
            rooms=tuple(rooms),
            lesson_requirements=tuple(lesson_requirements),
            teacher_assignments=tuple(teacher_assignments),
            teacher_availability=tuple(teacher_availability),
            teacher_free_afternoons=tuple(teacher_free_afternoons),
            room_availability=tuple(room_availability),
            slots=tuple(slots),
        )
