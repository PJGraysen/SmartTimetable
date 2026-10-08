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

# =========================================================================
# School events — for the home calendar widget
# =========================================================================
class SchoolEvent(models.Model):
    class Kind(models.TextChoices):
        HOLIDAY = "HOLIDAY", "Holiday"
        EXAM = "EXAM", "Exam"
        MEETING = "MEETING", "Meeting"
        SPORTS = "SPORTS", "Sports"
        ACTIVITY = "ACTIVITY", "Activity"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(primary_key=True, default=__import__("uuid").uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=200)
    date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name = "School event"
        verbose_name_plural = "School events"

    def __str__(self):
        return f"{self.date} - {self.title}"

# ------------------------------------------------------------------
# Notifications + Approval requests (SmartTimetable Pro)
# ------------------------------------------------------------------
from django.conf import settings as _N_settings
from django.db import models as _N_models
from django.utils import timezone as _N_tz


class Notification(_N_models.Model):
    """
    In-app notification. Recipients are users. Created via
    apps.core.notifications.notify() helper so all call sites go through
    one place.
    """

    class Kind(_N_models.TextChoices):
        INFO = "INFO", "Info"
        APPROVAL = "APPROVAL", "Approval needed"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REQUEST = "REQUEST", "Request"
        ALERT = "ALERT", "Alert"

    recipient = _N_models.ForeignKey(
        _N_settings.AUTH_USER_MODEL,
        on_delete=_N_models.CASCADE,
        related_name="notifications",
    )
    kind = _N_models.CharField(max_length=12, choices=Kind.choices, default=Kind.INFO)
    title = _N_models.CharField(max_length=200)
    body = _N_models.TextField(blank=True, default="")
    url = _N_models.CharField(max_length=300, blank=True, default="",
                              help_text="Deep link to open when clicked")
    is_read = _N_models.BooleanField(default=False)
    created_at = _N_models.DateTimeField(auto_now_add=True)
    read_at = _N_models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            _N_models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = _N_tz.now()
            self.save(update_fields=["is_read", "read_at"])

    def __str__(self):
        return f"[{self.kind}] {self.recipient} - {self.title}"


class ApprovalRequest(_N_models.Model):
    """
    A request from one user (or system) that needs approval by another.

    Used for:
      - inventory asset deletion (teacher -> principal)
      - library book requests (student -> teacher -> librarian -> student)
      - result publication (academics head -> principal)
    """

    class Kind(_N_models.TextChoices):
        INVENTORY_DELETE = "INVENTORY_DELETE", "Inventory deletion"
        BOOK_REQUEST = "BOOK_REQUEST", "Book request"
        RESULT_PUBLISH = "RESULT_PUBLISH", "Result publication"
        OTHER = "OTHER", "Other"

    class Status(_N_models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    kind = _N_models.CharField(max_length=24, choices=Kind.choices)
    status = _N_models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    requested_by = _N_models.ForeignKey(
        _N_settings.AUTH_USER_MODEL,
        on_delete=_N_models.CASCADE,
        related_name="approval_requests_made",
    )
    assigned_to = _N_models.ForeignKey(
        _N_settings.AUTH_USER_MODEL,
        on_delete=_N_models.CASCADE,
        related_name="approval_requests_pending",
    )

    title = _N_models.CharField(max_length=200)
    body = _N_models.TextField(blank=True, default="")

    # Generic FK target so we can attach a request to any model
    target_type = _N_models.CharField(max_length=64, blank=True, default="")
    target_id = _N_models.CharField(max_length=64, blank=True, default="")
    payload = _N_models.JSONField(default=dict, blank=True)

    created_at = _N_models.DateTimeField(auto_now_add=True)
    decided_at = _N_models.DateTimeField(null=True, blank=True)
    decision_note = _N_models.TextField(blank=True, default="")

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            _N_models.Index(fields=["assigned_to", "status", "-created_at"]),
        ]

    def approve(self, user, note=""):
        self.status = self.Status.APPROVED
        self.decided_at = _N_tz.now()
        self.decision_note = note
        self.save(update_fields=["status", "decided_at", "decision_note"])

    def reject(self, user, note=""):
        self.status = self.Status.REJECTED
        self.decided_at = _N_tz.now()
        self.decision_note = note
        self.save(update_fields=["status", "decided_at", "decision_note"])

    def __str__(self):
        return f"[{self.kind}] {self.title} -> {self.assigned_to} ({self.status})"
