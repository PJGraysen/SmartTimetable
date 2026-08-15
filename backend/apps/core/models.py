import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model providing creation and modification timestamps.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class School(TimeStampedModel):
    """
    Represents the institution using SmartTimetable Pro.
    """

    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "school"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AcademicYear(TimeStampedModel):
    """
    Represents an academic year belonging to a school.
    """

    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name="academic_years",
    )
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "academic_year"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"],
                name="uq_academic_year_school_name",
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="ck_academic_year_dates",
            ),
        ]

    def __str__(self):
        return self.name


class Term(TimeStampedModel):
    """
    Represents an academic term within an academic year.
    """

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="terms",
    )
    name = models.CharField(max_length=50)
    number = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "term"
        ordering = ["academic_year", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "number"],
                name="uq_term_academic_year_number",
            ),
            models.UniqueConstraint(
                fields=["academic_year", "name"],
                name="uq_term_academic_year_name",
            ),
            models.CheckConstraint(
                condition=models.Q(number__gte=1),
                name="ck_term_number_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="ck_term_dates",
            ),
        ]

    def __str__(self):
        return f"{self.academic_year.name} - {self.name}"