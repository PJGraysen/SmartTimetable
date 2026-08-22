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
    Represents an administrative teaching group.

    A teaching group may represent a complete stream or class. Learners
    within the teaching group may subsequently be divided into
    instructional groups for subject-specific scheduling.
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


class InstructionalGroup(TimeStampedModel):
    """
    Represents a schedulable cohort of learners within a teaching group.

    A teaching group represents the administrative class/stream, while an
    instructional group represents the actual learner cohort that attends
    particular lessons together.

    Examples:
        Form 3E - Core
        Form 3E - Physics
        Form 3E - Computer Studies
        Grade 10A - Agriculture
    """

    teaching_group = models.ForeignKey(
        TeachingGroup,
        on_delete=models.PROTECT,
        related_name="instructional_groups",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    learner_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "instructional_group"
        ordering = ["teaching_group", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["teaching_group", "name"],
                name="uq_instructional_group_teaching_group_name",
            ),
            models.UniqueConstraint(
                fields=["teaching_group", "code"],
                name="uq_instructional_group_teaching_group_code",
            ),
            models.CheckConstraint(
                condition=models.Q(learner_count__gte=0),
                name="ck_instructional_group_learner_count",
            ),
        ]

    def __str__(self):
        return f"{self.teaching_group} - {self.name}"


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
    Defines the teaching requirement for a subject and instructional group.

    This represents how many lessons of a subject an instructional group
    requires within the applicable term.
    """

    term = models.ForeignKey(
        "core.Term",
        on_delete=models.PROTECT,
        related_name="lesson_requirements",
    )
    instructional_group = models.ForeignKey(
        InstructionalGroup,
        on_delete=models.PROTECT,
        related_name="lesson_requirements",
        null=True,
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
        ordering = ["instructional_group", "subject"]
        constraints = [
            models.UniqueConstraint(
                fields=["term", "instructional_group", "subject"],
                name="uq_lesson_requirement_term_instructional_group_subject",
            ),
            models.CheckConstraint(
                condition=models.Q(lessons_per_week__gte=1),
                name="ck_lesson_requirement_lessons_positive",
            ),
        ]

    def __str__(self):
        return (
            f"{self.instructional_group} - "
            f"{self.subject} ({self.lessons_per_week}/week)"
        )
