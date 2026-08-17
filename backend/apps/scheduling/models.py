from django.core.exceptions import ValidationError
from django.db import models

from apps.academics.models import LessonRequirement, TeachingGroup, Subject
from apps.core.models import AcademicYear, School, Term, TimeStampedModel
from apps.users.models import Teacher


class DayOfWeek(models.TextChoices):
    MONDAY = "MON", "Monday"
    TUESDAY = "TUE", "Tuesday"
    WEDNESDAY = "WED", "Wednesday"
    THURSDAY = "THU", "Thursday"
    FRIDAY = "FRI", "Friday"


class PeriodPart(models.TextChoices):
    MORNING = "MORNING", "Morning"
    AFTERNOON = "AFTERNOON", "Afternoon"
    OTHER = "OTHER", "Other"


class Period(TimeStampedModel):
    """
    Represents a timetable period.

    Periods are classified by part of the school day so that scheduling
    rules such as the mandatory teacher free-afternoon constraint can
    identify all afternoon teaching periods without relying on hard-coded
    period numbers.
    """

    name = models.CharField(max_length=50)
    number = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    is_teaching_period = models.BooleanField(default=True)
    part_of_day = models.CharField(
        max_length=10,
        choices=PeriodPart.choices,
        default=PeriodPart.OTHER,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "period"
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["number"],
                name="uq_period_number",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    end_time__gt=models.F("start_time")
                ),
                name="ck_period_times",
            ),
        ]

    def clean(self):
        super().clean()

        if self.is_teaching_period and self.part_of_day == PeriodPart.OTHER:
            raise ValidationError(
                {
                    "part_of_day": (
                        "Teaching periods must be classified as "
                        "morning or afternoon."
                    )
                }
            )

    def __str__(self):
        return f"{self.number}: {self.name}"


class TeacherAssignment(TimeStampedModel):
    """
    Defines a teacher's eligibility/responsibility for a lesson requirement.

    A lesson requirement may have more than one eligible teacher. The
    scheduling engine can therefore choose among valid teachers.
    """

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="teaching_assignments",
    )
    lesson_requirement = models.ForeignKey(
        LessonRequirement,
        on_delete=models.PROTECT,
        related_name="teacher_assignments",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "teacher_assignment"
        ordering = ["teacher", "lesson_requirement"]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "lesson_requirement"],
                name="uq_teacher_assignment_teacher_requirement",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.lesson_requirement_id
            and self.teacher_id
            and not self.teacher.is_active
        ):
            raise ValidationError(
                {"teacher": "An inactive teacher cannot receive an assignment."}
            )

    def __str__(self):
        return (
            f"{self.teacher} - "
            f"{self.lesson_requirement}"
        )


class TeacherAvailability(TimeStampedModel):
    """
    Defines teacher availability for a specific term, day and period.

    An explicit record represents the teacher's availability state for
    that slot.
    """

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="teacher_availability",
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="availability",
    )
    day = models.CharField(
        max_length=3,
        choices=DayOfWeek.choices,
    )
    period = models.ForeignKey(
        Period,
        on_delete=models.PROTECT,
        related_name="teacher_availability",
    )
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "teacher_availability"
        ordering = ["teacher", "day", "period__number"]
        constraints = [
            models.UniqueConstraint(
                fields=["term", "teacher", "day", "period"],
                name="uq_teacher_availability_slot",
            ),
        ]
        indexes = [
            models.Index(
                fields=["term", "teacher"],
                name="ix_teacher_avail_term_teacher",
            ),
            models.Index(
                fields=["term", "day", "period"],
                name="ix_teacher_availability_slot",
            ),
        ]

    def __str__(self):
        return (
            f"{self.teacher} - "
            f"{self.day} - "
            f"{self.period}"
        )


class TeacherFreeAfternoon(TimeStampedModel):
    """
    Defines the mandatory free-afternoon assignment for a teacher.

    Each teacher must have exactly one designated free-afternoon day
    within the applicable scheduling term.

    All afternoon teaching periods on that day are protected from
    timetable assignment for that teacher.
    """

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="teacher_free_afternoons",
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="free_afternoons",
    )
    day = models.CharField(
        max_length=3,
        choices=DayOfWeek.choices,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "teacher_free_afternoon"
        ordering = ["teacher", "day"]
        constraints = [
            models.UniqueConstraint(
                fields=["term", "teacher"],
                name="uq_teacher_free_afternoon_teacher_term",
            ),
        ]
        indexes = [
            models.Index(
                fields=["term", "day"],
                name="ix_teacher_free_term_day",
            ),
        ]

    def __str__(self):
        return f"{self.teacher} - {self.get_day_display()} free afternoon"


class Room(TimeStampedModel):
    """
    Represents a physical room/resource that can be used by a lesson.
    """

    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name="rooms",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "room"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"],
                name="uq_room_school_name",
            ),
            models.UniqueConstraint(
                fields=["school", "code"],
                name="uq_room_school_code",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class RoomAvailability(TimeStampedModel):
    """
    Defines room availability for a specific term, day and period.
    """

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="room_availability",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="availability",
    )
    day = models.CharField(
        max_length=3,
        choices=DayOfWeek.choices,
    )
    period = models.ForeignKey(
        Period,
        on_delete=models.PROTECT,
        related_name="room_availability",
    )
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "room_availability"
        ordering = ["room", "day", "period__number"]
        constraints = [
            models.UniqueConstraint(
                fields=["term", "room", "day", "period"],
                name="uq_room_availability_slot",
            ),
        ]
        indexes = [
            models.Index(
                fields=["term", "room"],
                name="ix_room_availability_term_room",
            ),
            models.Index(
                fields=["term", "day", "period"],
                name="ix_room_availability_slot",
            ),
        ]

    def __str__(self):
        return (
            f"{self.room} - "
            f"{self.day} - "
            f"{self.period}"
        )


class TimetableVersion(TimeStampedModel):
    """
    Represents a version of a timetable for an academic term.

    Multiple versions may exist for the same term to preserve timetable
    history and support draft, published and archived schedules.
    """

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="timetable_versions",
    )
    name = models.CharField(max_length=100)
    version_number = models.PositiveIntegerField()
    is_published = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "timetable_version"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["term", "version_number"],
                name="uq_timetable_version_term_number",
            ),
            models.UniqueConstraint(
                fields=["term", "name"],
                name="uq_timetable_version_term_name",
            ),
        ]

    def __str__(self):
        return f"{self.term} - {self.name}"


class TimetableEntry(TimeStampedModel):
    """
    Represents one scheduled lesson within a timetable version.
    """

    timetable_version = models.ForeignKey(
        TimetableVersion,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    day = models.CharField(
        max_length=3,
        choices=DayOfWeek.choices,
    )
    period = models.ForeignKey(
        Period,
        on_delete=models.PROTECT,
        related_name="timetable_entries",
    )
    teaching_group = models.ForeignKey(
        TeachingGroup,
        on_delete=models.PROTECT,
        related_name="timetable_entries",
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="timetable_entries",
    )
    lesson_requirement = models.ForeignKey(
        LessonRequirement,
        on_delete=models.PROTECT,
        related_name="timetable_entries",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="timetable_entries",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "timetable_entry"
        ordering = ["day", "period__number"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "timetable_version",
                    "day",
                    "period",
                    "teaching_group",
                ],
                name="uq_timetable_entry_group_slot",
            ),
            models.UniqueConstraint(
                fields=[
                    "timetable_version",
                    "day",
                    "period",
                    "teacher",
                ],
                name="uq_timetable_entry_teacher_slot",
            ),
            models.UniqueConstraint(
                fields=[
                    "timetable_version",
                    "day",
                    "period",
                    "room",
                ],
                name="uq_timetable_entry_room_slot",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "timetable_version",
                    "day",
                    "period",
                ],
                name="ix_timetable_entry_slot",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.lesson_requirement_id:
            return

        requirement = self.lesson_requirement

        if self.teaching_group_id != requirement.teaching_group_id:
            raise ValidationError(
                {
                    "teaching_group": (
                        "The timetable entry teaching group must match "
                        "the lesson requirement teaching group."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.timetable_version} - "
            f"{self.day} - "
            f"{self.period} - "
            f"{self.teaching_group}"
        )