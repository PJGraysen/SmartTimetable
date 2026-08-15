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


class AuditLog(TimeStampedModel):
    """
    Records significant actions performed within SmartTimetable Pro.
    """

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
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="ix_audit_log_user_created",
            ),
            models.Index(
                fields=["entity_type", "entity_id"],
                name="ix_audit_log_entity",
            ),
            models.Index(
                fields=["action", "-created_at"],
                name="ix_audit_log_action_created",
            ),
        ]

    def __str__(self):
        return f"{self.action} - {self.entity_type} - {self.entity_id}"