from django.core.exceptions import ValidationError
from django.db import models

from apps.academics.models import (
    InstructionalGroup,
    LessonRequirement,
)
from apps.core.models import School, Term, TimeStampedModel
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

    The schedulable learner cohort is an InstructionalGroup rather than
    the administrative TeachingGroup.
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
    instructional_group = models.ForeignKey(
        InstructionalGroup,
        on_delete=models.PROTECT,
        related_name="timetable_entries",
        null=True,
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="timetable_entries",
        null=True,
        blank=True,
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
                    "instructional_group",
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

        if self.instructional_group_id != requirement.instructional_group_id:
            raise ValidationError(
                {
                    "instructional_group": (
                        "The timetable entry instructional group must match "
                        "the lesson requirement instructional group."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.timetable_version} - "
            f"{self.day} - "
            f"{self.period} - "
            f"{self.instructional_group}"
        )


class SchedulingRunStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class SolverStatus(models.TextChoices):
    NOT_RUN = "NOT_RUN", "Not Run"
    FEASIBLE = "FEASIBLE", "Feasible"
    OPTIMAL = "OPTIMAL", "Optimal"
    INFEASIBLE = "INFEASIBLE", "Infeasible"
    UNKNOWN = "UNKNOWN", "Unknown"
    ERROR = "ERROR", "Error"


class ValidationSeverity(models.TextChoices):
    ERROR = "ERROR", "Error"
    WARNING = "WARNING", "Warning"
    INFO = "INFO", "Information"


class ValidationCategory(models.TextChoices):
    TEACHER_CLASH = "TEACHER_CLASH", "Teacher Clash"
    GROUP_CLASH = "GROUP_CLASH", "Teaching Group Clash"
    ROOM_CLASH = "ROOM_CLASH", "Room Clash"
    TEACHER_UNAVAILABLE = "TEACHER_UNAVAILABLE", "Teacher Unavailable"
    ROOM_UNAVAILABLE = "ROOM_UNAVAILABLE", "Room Unavailable"
    FREE_AFTERNOON_VIOLATION = (
        "FREE_AFTERNOON_VIOLATION",
        "Free Afternoon Violation",
    )
    MISSING_TEACHER_ASSIGNMENT = (
        "MISSING_TEACHER_ASSIGNMENT",
        "Missing Teacher Assignment",
    )
    INVALID_LESSON_REQUIREMENT = (
        "INVALID_LESSON_REQUIREMENT",
        "Invalid Lesson Requirement",
    )
    INVALID_PERIOD = "INVALID_PERIOD", "Invalid Period"
    INVALID_TIMETABLE_ENTRY = (
        "INVALID_TIMETABLE_ENTRY",
        "Invalid Timetable Entry",
    )
    UNSCHEDULED_LESSON = "UNSCHEDULED_LESSON", "Unscheduled Lesson"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION", "Constraint Violation"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR", "Configuration Error"
    OTHER = "OTHER", "Other"


class SchedulingRun(TimeStampedModel):
    """
    Represents one attempt to generate or validate a timetable.

    A scheduling run records the execution lifecycle and solver outcome
    without storing solver implementation details in the timetable models.
    """

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="scheduling_runs",
    )
    timetable_version = models.ForeignKey(
        TimetableVersion,
        on_delete=models.PROTECT,
        related_name="scheduling_runs",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=SchedulingRunStatus.choices,
        default=SchedulingRunStatus.PENDING,
    )
    solver_status = models.CharField(
        max_length=20,
        choices=SolverStatus.choices,
        default=SolverStatus.NOT_RUN,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objective_value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    statistics = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "scheduling_run"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["term", "status"],
                name="ix_scheduling_run_term_status",
            ),
            models.Index(
                fields=["timetable_version"],
                name="ix_scheduling_run_version",
            ),
        ]

    def __str__(self):
        return f"{self.term} - {self.status}"


class ValidationResult(TimeStampedModel):
    """
    Represents one validation finding associated with a scheduling run.

    Validation results may refer to the specific teacher, instructional
    group, period, room, or timetable entry involved in the finding.
    """

    scheduling_run = models.ForeignKey(
        SchedulingRun,
        on_delete=models.CASCADE,
        related_name="validation_results",
    )

    severity = models.CharField(
        max_length=10,
        choices=ValidationSeverity.choices,
    )

    category = models.CharField(
        max_length=40,
        choices=ValidationCategory.choices,
    )

    message = models.TextField()

    details = models.JSONField(
        default=dict,
        blank=True,
    )

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="validation_results",
        null=True,
        blank=True,
    )

    instructional_group = models.ForeignKey(
        InstructionalGroup,
        on_delete=models.PROTECT,
        related_name="validation_results",
        null=True,
        blank=True,
    )

    period = models.ForeignKey(
        Period,
        on_delete=models.PROTECT,
        related_name="validation_results",
        null=True,
        blank=True,
    )

    day = models.CharField(
        max_length=3,
        choices=DayOfWeek.choices,
        null=True,
        blank=True,
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="validation_results",
        null=True,
        blank=True,
    )

    timetable_entry = models.ForeignKey(
        TimetableEntry,
        on_delete=models.PROTECT,
        related_name="validation_results",
        null=True,
        blank=True,
    )

    is_resolved = models.BooleanField(default=False)

    class Meta:
        db_table = "validation_result"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["scheduling_run", "severity"],
                name="ix_validation_run_severity",
            ),
            models.Index(
                fields=["scheduling_run", "category"],
                name="ix_validation_run_category",
            ),
        ]

    def __str__(self):
        return f"{self.severity} - {self.category}"
