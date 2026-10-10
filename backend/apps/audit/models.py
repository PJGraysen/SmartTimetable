from django.contrib.auth.models import User
from django.db import models

from apps.core.models import TimeStampedModel


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Create"
    UPDATE = "UPDATE", "Update"
    DELETE = "DELETE", "Delete"
    PUBLISH = "PUBLISH", "Publish"
    UNPUBLISH = "UNPUBLISH", "Unpublish"
    GENERATE = "GENERATE", "Generate"
    VALIDATE = "VALIDATE", "Validate"
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    ERROR = "ERROR", "Error"


class AuditLog(TimeStampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    action = models.CharField(
        max_length=20,
        choices=AuditAction.choices,
    )
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["action", "-created_at"],
                name="audit_action_created_idx",
            ),
            models.Index(
                fields=["entity_type", "entity_id"],
                name="audit_entity_idx",
            ),
        ]

    def __str__(self):
        return f"{self.action} - {self.entity_type} - {self.entity_id}"


class ErrorSeverity(models.TextChoices):
    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    ERROR = "ERROR", "Error"
    CRITICAL = "CRITICAL", "Critical"


class ErrorStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    RESOLVED = "RESOLVED", "Resolved"


class ErrorRecord(TimeStampedModel):
    """
    Persistent operational error record.

    This is deliberately separate from AuditLog:
    AuditLog records user/business actions; ErrorRecord records failures,
    warnings and operational exceptions that must remain inspectable.
    """

    occurred_at = models.DateTimeField(auto_now_add=True)

    severity = models.CharField(
        max_length=20,
        choices=ErrorSeverity.choices,
        default=ErrorSeverity.ERROR,
    )

    status = models.CharField(
        max_length=20,
        choices=ErrorStatus.choices,
        default=ErrorStatus.OPEN,
    )

    subsystem = models.CharField(max_length=100)
    operation = models.CharField(max_length=150)
    error_code = models.CharField(max_length=100)

    message = models.TextField()
    technical_exception = models.TextField(blank=True)
    traceback = models.TextField(blank=True)

    entity_type = models.CharField(max_length=100, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)

    affected_teacher = models.CharField(max_length=150, blank=True)
    affected_class = models.CharField(max_length=150, blank=True)
    affected_subject = models.CharField(max_length=150, blank=True)

    solver_run_id = models.CharField(max_length=150, blank=True)

    resolution = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="error_records",
    )

    class Meta:
        db_table = "error_record"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(
                fields=["severity", "-occurred_at"],
                name="error_severity_time_idx",
            ),
            models.Index(
                fields=["status", "-occurred_at"],
                name="error_status_time_idx",
            ),
            models.Index(
                fields=["subsystem", "-occurred_at"],
                name="error_subsystem_time_idx",
            ),
            models.Index(
                fields=["error_code", "-occurred_at"],
                name="error_code_time_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.severity} - {self.subsystem} - "
            f"{self.error_code} - {self.message[:80]}"
        )


# ---------------------------------------------------------------------
# UserHeartbeat  (Layer 3 ? live activity tracking)
# ---------------------------------------------------------------------
class UserHeartbeat(TimeStampedModel):
    """Last time each user touched the app. Updated by /api/audit/heartbeat/."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="heartbeat",
    )
    last_seen = models.DateTimeField(auto_now=True, db_index=True)
    last_path = models.CharField(max_length=500, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "user_heartbeat"
        ordering = ["-last_seen"]

    def __str__(self):
        return f"{self.user} @ {self.last_seen}"


# ---------------------------------------------------------------------
# Login security (2026-10-09)
# ---------------------------------------------------------------------
class LoginOutcome(models.TextChoices):
    SUCCESS          = "SUCCESS",          "Success"
    BAD_PASSWORD     = "BAD_PASSWORD",     "Bad password"
    BAD_CODE         = "BAD_CODE",         "Bad verification code"
    NO_SUCH_USER     = "NO_SUCH_USER",     "No such user"
    INACTIVE         = "INACTIVE",         "Account inactive"
    THROTTLED        = "THROTTLED",        "Rate limited"
    LOCKED           = "LOCKED",           "Account locked"
    PENDING_VERIFY   = "PENDING_VERIFY",   "Awaiting verification"


class LoginAttempt(TimeStampedModel):
    """Every login attempt ? good or bad. Immutable audit record."""
    username_attempted = models.CharField(max_length=150, db_index=True)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="login_attempts",
    )
    outcome = models.CharField(max_length=20, choices=LoginOutcome.choices, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    device_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "login_attempt"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["username_attempted", "-created_at"]),
            models.Index(fields=["ip_address", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.username_attempted} {self.outcome}"


class VerificationChannel(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    PHONE = "PHONE", "Phone"


class UserSecurity(TimeStampedModel):
    """Per-user security state: failed attempts, lockout, 2FA-lite."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="security",
    )
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    requires_verification = models.BooleanField(default=False)
    verification_code_hash = models.CharField(max_length=128, blank=True)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    verification_purpose = models.CharField(max_length=40, blank=True)
    preferred_channel = models.CharField(
        max_length=10, choices=VerificationChannel.choices,
        default=VerificationChannel.EMAIL,
    )
    last_successful_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_security"

    def __str__(self):
        return f"Security({self.user.username})"

    def is_locked(self):
        from django.utils import timezone
        return self.locked_until is not None and self.locked_until > timezone.now()


def security_for(user):
    """Return the UserSecurity row for a user, creating if needed."""
    obj, _ = UserSecurity.objects.get_or_create(user=user)
    return obj
