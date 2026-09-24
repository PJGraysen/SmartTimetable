from django.contrib import admin

from .models import AuditLog, ErrorRecord


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "entity_type",
        "entity_id",
        "user",
        "description",
    )
    list_filter = ("action", "entity_type")
    search_fields = (
        "entity_type",
        "entity_id",
        "description",
        "user__username",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)


@admin.register(ErrorRecord)
class ErrorRecordAdmin(admin.ModelAdmin):
    list_display = (
        "occurred_at",
        "severity",
        "status",
        "subsystem",
        "operation",
        "error_code",
        "entity_type",
        "entity_id",
    )
    list_filter = (
        "severity",
        "status",
        "subsystem",
    )
    search_fields = (
        "message",
        "technical_exception",
        "traceback",
        "error_code",
        "subsystem",
        "operation",
        "entity_type",
        "entity_id",
        "affected_teacher",
        "affected_class",
        "affected_subject",
        "solver_run_id",
        "resolution",
    )
    readonly_fields = (
        "occurred_at",
        "created_at",
        "updated_at",
    )
    ordering = ("-occurred_at",)
    date_hierarchy = "occurred_at"
