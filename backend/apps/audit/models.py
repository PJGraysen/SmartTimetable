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
