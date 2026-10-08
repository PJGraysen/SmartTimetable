from django.contrib.auth.models import User
from django.db import models

from apps.core.models import TimeStampedModel


class DutyPreference(models.TextChoices):
    ANY      = "ANY", "Any shift (day or night)"
    DAY_ONLY = "DAY_ONLY", "Day shift only"


class Teacher(TimeStampedModel):
    """
    Represents a teacher who can be assigned teaching responsibilities
    and scheduled for lessons.

    employee_code:
        Administrative/HR identifier, e.g. EMP001.

    teacher_number:
        Numeric identifier used on published timetables, e.g. 19.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="teacher_profile",
    )

    employee_code = models.CharField(
        max_length=50,
        unique=True,
    )

    teacher_number = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Numeric teacher number displayed on timetables.",
    )

    first_name = models.CharField(
        max_length=100,
    )

    last_name = models.CharField(
        max_length=100,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_frozen = models.BooleanField(default=False)
    duty_eligible = models.BooleanField(
        default=True,
        help_text="If False, teacher is skipped in duty roster rotation (e.g. librarian, principal).",
    )

    duty_preference = models.CharField(
        max_length=20,
        choices=DutyPreference.choices,
        default=DutyPreference.ANY,
    )

    # ---- Extended profile (SmartTimetable Pro) ----
    ROLE_CHOICES = [
        ("SUPER_ADMIN", "Super Admin (full access)"),
        ("PRINCIPAL", "Principal / Rector"),
        ("SECRETARY", "Secretary"),
        ("DEPT_HEAD", "Department Head"),
        ("TEACHER", "Teacher"),
        ("LAB_TECH", "Lab Technician"),
        ("AUDITOR", "Internal Auditor"),
        ("PROCUREMENT", "Procurement Officer"),
        ("LIBRARIAN", "Librarian"),
        ("BURSAR", "Bursar"),
        ("OTHER", "Other Staff"),
    ]

    role = models.CharField(
        max_length=24,
        choices=ROLE_CHOICES,
        default="TEACHER",
        help_text="Operational role in the school",
    )
    department = models.ForeignKey(
        "inventory.Department",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="teachers",
        help_text="Home department (Science, Maths, ICT...)",
    )
    phone = models.CharField(max_length=40, blank=True)
    hire_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "teacher"
        ordering = ["teacher_number", "last_name", "first_name"]

    def save(self, *args, **kwargs):
        """
        Automatically assign the lowest available timetable number.

        Existing teacher numbers are preserved. New teachers receive
        a unique number from 1 through 100.
        """
        if self.teacher_number is None:
            used_numbers = set(
                Teacher.objects.exclude(
                    teacher_number__isnull=True,
                ).values_list(
                    "teacher_number",
                    flat=True,
                )
            )

            available_numbers = (
                number
                for number in range(1, 101)
                if number not in used_numbers
            )

            try:
                self.teacher_number = next(available_numbers)
            except StopIteration:
                raise ValueError(
                    "No teacher numbers are available. "
                    "The maximum supported teacher number is 100."
                )

        super().save(*args, **kwargs)
    def __str__(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()

        if name:
            return f"{self.employee_code} - {name}"

        return self.employee_code

