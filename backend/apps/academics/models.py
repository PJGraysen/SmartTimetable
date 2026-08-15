from django.db import models

from apps.core.models import AcademicYear, TimeStampedModel


class Grade(TimeStampedModel):
    """
    Represents a grade/form level within an academic year.
    """

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="grades",
    )
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20)

    class Meta:
        db_table = "grade"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "name"],
                name="uq_grade_academic_year_name",
            ),
            models.UniqueConstraint(
                fields=["academic_year", "code"],
                name="uq_grade_academic_year_code",
            ),
        ]

    def __str__(self):
        return self.name


class Stream(TimeStampedModel):
    """
    Represents a stream belonging to a grade.
    """

    grade = models.ForeignKey(
        Grade,
        on_delete=models.PROTECT,
        related_name="streams",
    )
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20)

    class Meta:
        db_table = "stream"
        ordering = ["grade", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["grade", "name"],
                name="uq_stream_grade_name",
            ),
            models.UniqueConstraint(
                fields=["grade", "code"],
                name="uq_stream_grade_code",
            ),
        ]

    def __str__(self):
        return f"{self.grade.name} - {self.name}"


class TeachingGroup(TimeStampedModel):
    """
    Represents a group of learners receiving instruction.

    A teaching group may represent a complete stream or a subject-specific
    grouping where learners are divided according to subject choices.
    """

    stream = models.ForeignKey(
        Stream,
        on_delete=models.PROTECT,
        related_name="teaching_groups",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    learner_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "teaching_group"
        ordering = ["stream", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["stream", "name"],
                name="uq_teaching_group_stream_name",
            ),
            models.UniqueConstraint(
                fields=["stream", "code"],
                name="uq_teaching_group_stream_code",
            ),
            models.CheckConstraint(
                condition=models.Q(learner_count__gte=0),
                name="ck_teaching_group_learner_count",
            ),
        ]

    def __str__(self):
        return f"{self.stream} - {self.name}"


class Subject(TimeStampedModel):
    """
    Represents a subject taught within the school.
    """

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subject"
        ordering = ["name"]

    def __str__(self):
        return self.name


class LessonRequirement(TimeStampedModel):
    """
    Defines the teaching requirement for a subject and teaching group.

    This represents how many lessons of a subject a teaching group requires
    within the applicable term.
    """

    term = models.ForeignKey(
        "core.Term",
        on_delete=models.PROTECT,
        related_name="lesson_requirements",
    )
    teaching_group = models.ForeignKey(
        TeachingGroup,
        on_delete=models.PROTECT,
        related_name="lesson_requirements",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="lesson_requirements",
    )
    lessons_per_week = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "lesson_requirement"
        ordering = ["teaching_group", "subject"]
        constraints = [
            models.UniqueConstraint(
                fields=["term", "teaching_group", "subject"],
                name="uq_lesson_requirement_term_group_subject",
            ),
            models.CheckConstraint(
                condition=models.Q(lessons_per_week__gte=1),
                name="ck_lesson_requirement_lessons_positive",
            ),
        ]

    def __str__(self):
        return (
            f"{self.teaching_group} - "
            f"{self.subject} ({self.lessons_per_week}/week)"
        )