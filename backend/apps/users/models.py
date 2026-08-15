from django.contrib.auth.models import User
from django.db import models

from apps.core.models import TimeStampedModel


class Teacher(TimeStampedModel):
    """
    Represents a teacher who can be assigned teaching responsibilities
    and scheduled for lessons.
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
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "teacher"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"