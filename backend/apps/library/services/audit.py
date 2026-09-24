from __future__ import annotations

from apps.audit.models import AuditLog


# AuditLog.action is CharField(max_length=20). This helper guarantees
# we never overflow the column regardless of caller-provided code.
_ACTION_MAX = 20


def log_library_action(
    *,
    user,
    action: str,
    entity_type: str,
    entity_id: str,
    description: str,
) -> None:
    safe_action = str(action)[:_ACTION_MAX]
    AuditLog.objects.create(
        user=user,
        action=safe_action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        description=description,
    )
