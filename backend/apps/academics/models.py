from django.db import models

from apps.core.models import AcademicYear, TimeStampedModel
from apps.academics.domain.lesson_requirement_types import LessonRequirementType


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

    # ---- L4 / dashboard thumbnails ----
    icon = models.CharField(
        max_length=8, blank=True, default="",
        help_text="Single emoji shown as the subject tile on the library dashboard.",
    )
    thumbnail_url = models.URLField(
        blank=True, default="",
        help_text="Optional image URL. When empty, the emoji tile is used.",
    )
    colour = models.CharField(
        max_length=16, blank=True, default="",
        help_text="Optional hex colour for the tile background (e.g. #1e3a8a).",
    )

    class Meta:
        db_table = "subject"
        ordering = ["name"]

    def __str__(self):
        return self.name


class LessonRequirement(TimeStampedModel):
    """
    Defines a teaching requirement for a subject and instructional group.

    A requirement is structurally classified as:

    STANDALONE:
        Ordinary subject teaching.

    BLOCK:
        Subject teaching belonging to a synchronized elective/curriculum
        block.

    PRACTICAL:
        Additional practical teaching attached to a subject which may also
        have a separate BLOCK requirement.

    BLOCK and PRACTICAL are intentionally separate requirements. This allows
    teacher assignment, lesson counts, scheduling constraints, and solver
    behavior to remain structurally correct.
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
    requirement_type = models.CharField(
        max_length=16,
        choices=LessonRequirementType.choices,
        default=LessonRequirementType.STANDALONE,
    )
    teacher = models.ForeignKey(
        "users.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_requirements",
    )
    lessons_per_week = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "lesson_requirement"
        ordering = [
            "instructional_group",
            "subject",
            "requirement_type",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "term",
                    "instructional_group",
                    "subject",
                    "requirement_type",
                ],
                name="uq_lesson_requirement_term_group_subject_type",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    lessons_per_week__gte=1,
                ),
                name="ck_lesson_requirement_lessons_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    requirement_type__in=[
                        LessonRequirementType.STANDALONE,
                        LessonRequirementType.BLOCK,
                        LessonRequirementType.PRACTICAL,
                    ],
                ),
                name="ck_lesson_requirement_type_valid",
            ),
        ]

    def __str__(self):
        return (
            f"{self.instructional_group} - "
            f"{self.subject} - "
            f"{self.requirement_type} "
            f"({self.lessons_per_week}/week)"
        )




# =====================================================================
#  Academic student records (added 2026-09-16)
# =====================================================================

class StudentGender(models.TextChoices):
    MALE = "M", "Male"
    FEMALE = "F", "Female"


class StudentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    GRADUATED = "GRADUATED", "Graduated"
    TRANSFERRED = "TRANSFERRED", "Transferred"
    SUSPENDED = "SUSPENDED", "Suspended"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class Student(TimeStampedModel):
    """
    Persistent academic identity for a learner.

    Independent of any single grade, stream, or assessment. Current
    class membership is expressed via StudentEnrollment so that
    historical placement is preserved.
    """

    admission_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100)

    gender = models.CharField(
        max_length=1,
        choices=StudentGender.choices,
        blank=True,
        default="",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    kcpe_mark = models.PositiveIntegerField(null=True, blank=True)
    admission_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "student"
        ordering = ["last_name", "first_name", "admission_number"]
        indexes = [
            models.Index(fields=["admission_number"]),
            models.Index(fields=["is_active", "status"]),
        ]

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p).strip()

    def __str__(self) -> str:
        return f"{self.admission_number} - {self.full_name}"


class StudentEnrollment(TimeStampedModel):
    """
    A student's membership in a teaching group for a given academic
    year. Closing an enrollment sets left_on and is_current=False
    rather than deleting the row, preserving history.
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="student_enrollments",
    )
    teaching_group = models.ForeignKey(
        TeachingGroup,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    joined_on = models.DateField()
    left_on = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        db_table = "student_enrollment"
        ordering = ["-is_current", "-joined_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "academic_year"],
                condition=models.Q(is_current=True),
                name="uq_student_current_enrollment_per_year",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student.admission_number} -> {self.teaching_group.name}"



# =====================================================================
#  Assessment / Result / Grading (added 2026-09-16)
# =====================================================================

class AssessmentType(models.TextChoices):
    CAT = "CAT", "Continuous Assessment Test"
    MIDTERM = "MIDTERM", "Mid-Term Examination"
    ENDTERM = "ENDTERM", "End-Term Examination"
    MOCK = "MOCK", "Mock Examination"
    INTERNAL = "INTERNAL", "Internal Assessment"


class AssessmentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    MARK_ENTRY = "MARK_ENTRY", "Mark Entry"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED = "ARCHIVED", "Archived"


class Assessment(TimeStampedModel):
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="assessments",
    )
    term = models.ForeignKey(
        "core.Term", on_delete=models.PROTECT, related_name="assessments",
    )
    name = models.CharField(max_length=120)
    assessment_type = models.CharField(
        max_length=20, choices=AssessmentType.choices,
        default=AssessmentType.ENDTERM,
    )
    date = models.DateField()
    max_mark = models.PositiveIntegerField(default=100)
    status = models.CharField(
        max_length=20, choices=AssessmentStatus.choices,
        default=AssessmentStatus.PUBLISHED,
    )

    class Meta:
        db_table = "assessment"
        ordering = ["date", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "term", "name"],
                name="uq_assessment_year_term_name",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.date})"


class ResultStatus(models.TextChoices):
    VALID = "VALID", "Valid"
    ABSENT = "ABSENT", "Absent"
    MISSING = "MISSING", "Missing"
    EXEMPT = "EXEMPT", "Exempt"
    NOT_ASSESSED = "NOT_ASSESSED", "Not Assessed"


class Result(TimeStampedModel):
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="results",
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="results",
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="results",
    )
    raw_mark = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
    )
    status = models.CharField(
        max_length=20, choices=ResultStatus.choices,
        default=ResultStatus.VALID,
    )

    class Meta:
        db_table = "result"
        ordering = ["assessment", "student", "subject"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "student", "subject"],
                name="uq_result_assessment_student_subject",
            ),
        ]

    def __str__(self):
        return f"{self.student.admission_number} {self.subject.code} {self.raw_mark}"


class GradingScheme(TimeStampedModel):
    name = models.CharField(max_length=120)
    curriculum = models.CharField(max_length=60, blank=True, default="")
    effective_from = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "grading_scheme"
        ordering = ["-is_active", "name"]

    def __str__(self):
        return self.name


class GradingBand(TimeStampedModel):
    scheme = models.ForeignKey(
        GradingScheme, on_delete=models.CASCADE, related_name="bands",
    )
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=10)
    points = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    descriptor = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        db_table = "grading_band"
        ordering = ["scheme", "-min_score"]

    def __str__(self):
        return f"{self.scheme.name} {self.grade} ({self.min_score}-{self.max_score})"



# =====================================================================
#  Academic audit trail (RoE §26)
# =====================================================================
class AcademicAuditEvent(TimeStampedModel):
    """
    Immutable log of significant academic-data mutations.
    Read-only from the UI; entries are created by the audit helper.
    """

    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("PUBLISH", "Publish"),
        ("UNPUBLISH", "Unpublish"),
        ("ARCHIVE", "Archive"),
        ("BULK_UPDATE", "Bulk Update"),
        ("STATUS_CHANGE", "Status Change"),
    ]

    actor = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="academic_audit_events",
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField(null=True, blank=True)
    entity_label = models.CharField(max_length=255, blank=True, default="")
    meta_json = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        db_table = "academic_audit_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["actor"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type} — {self.entity_label}"



class ReportComment(TimeStampedModel):
    """
    Per-term narrative fields printed on the school report form.
    One row per (student, academic_year, term).
    """
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="report_comments",
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="report_comments",
    )
    term = models.ForeignKey(
        "core.Term", on_delete=models.PROTECT, related_name="report_comments",
    )
    conduct = models.CharField(max_length=200, blank=True, default="")
    class_teacher_comment = models.TextField(blank=True, default="")
    rector_comment = models.TextField(blank=True, default="")
    mission_comment = models.TextField(blank=True, default="")

    class Meta:
        db_table = "report_comment"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "academic_year", "term"],
                name="uq_report_comment_student_year_term",
            ),
        ]

    def __str__(self):
        return f"{self.student.admission_number} {self.term} comments"



class RankingMethod(models.TextChoices):
    TOTAL_MARKS = "TOTAL", "Total Marks"
    MEAN_PCT = "MEAN_PCT", "Mean Percentage"
    MEAN_POINTS = "MEAN_POINTS", "Mean Grade Points"
    SUBJECT_COMBO = "SUBJECT_COMBO", "Selected Subject Combination"


class TiePolicy(models.TextChoices):
    COMPETITION = "COMPETITION", "Competition (1, 2, 2, 4)"
    DENSE = "DENSE", "Dense (1, 2, 2, 3)"
    ORDINAL = "ORDINAL", "Ordinal (1, 2, 3, 4)"


class RankingRule(TimeStampedModel):
    """
    Configurable rule that defines how a ranking is produced.
    Versioned — every change bumps `version`, so past RankingRuns
    remain traceable to the exact rule that generated them.
    """
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    method = models.CharField(
        max_length=20, choices=RankingMethod.choices,
        default=RankingMethod.MEAN_PCT,
    )
    tie_policy = models.CharField(
        max_length=20, choices=TiePolicy.choices,
        default=TiePolicy.COMPETITION,
    )
    subject_codes = models.JSONField(default=list, blank=True)
    min_subjects = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "ranking_rule"
        ordering = ["-is_active", "name"]

    def to_snapshot(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "method": self.method,
            "tie_policy": self.tie_policy,
            "subject_codes": list(self.subject_codes or []),
            "min_subjects": self.min_subjects,
            "version": self.version,
        }

    def __str__(self):
        return f"{self.name} v{self.version}"


class RankingRun(TimeStampedModel):
    """
    Immutable snapshot of a ranking that was produced.
    Stores both the foreign key to the rule AND a frozen snapshot,
    so editing/deleting a rule later does not corrupt history.
    """
    rule = models.ForeignKey(
        RankingRule, on_delete=models.PROTECT, related_name="runs",
    )
    rule_snapshot = models.JSONField(default=dict)
    assessment = models.ForeignKey(
        "academics.Assessment", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="ranking_runs",
    )
    scope_type = models.CharField(max_length=20, default="CLASS")
    scope_id = models.UUIDField(null=True, blank=True)
    scope_label = models.CharField(max_length=200, blank=True, default="")
    entries = models.JSONField(default=list)
    student_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ranking_run"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rule.name} — {self.scope_label} — {self.created_at:%Y-%m-%d}"
