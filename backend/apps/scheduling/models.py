from django.db import models

from apps.academics.models import LessonRequirement, TeachingGroup
from apps.core.models import TimeStampedModel
from apps.users.models import Teacher


class DayOfWeek(models.TextChoices):
    MONDAY = "MON", "Monday"
    TUESDAY = "TUE", "Tuesday"
    WEDNESDAY = "WED", "Wednesday"
    THURSDAY = "THU", "Thursday"
    FRIDAY = "FRI", "Friday"


class Period(TimeStampedModel):
    """
    Represents a teaching period in the school timetable.

    A period defines the ordinal position and clock time of a lesson.
    """

    name = models.CharField(max_length=50)
    number = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_teaching_period = models.BooleanField(default=True)
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
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="ck_period_times",
            ),
        ]

    def __str__(self):
        return f"{self.number}: {self.name}"


class TimetableVersion(TimeStampedModel):
    """
    Represents a version of a timetable for an academic term.

    Multiple versions may exist for the same term to preserve timetable
    history and support draft, published, and archived schedules.
    """

    term = models.ForeignKey(
        "core.Term",
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
        ]

    def __str__(self):
        return (
            f"{self.timetable_version} - "
            f"{self.day} - "
            f"{self.period} - "
            f"{self.teaching_group}"
        )