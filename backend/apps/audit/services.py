from __future__ import annotations

import traceback
from typing import Any
from uuid import UUID


def _text(value: Any) -> str:
    """
    Convert optional ErrorRecord text context to a database-safe value.

    ErrorRecord uses NULL=False + blank=True for contextual CharField/TextField
    fields. Therefore unavailable context is represented by an empty string,
    never by None.
    """
    if value is None:
        return ""

    return str(value)


def capture_exception(
    *,
    exception: BaseException,
    subsystem: str,
    operation: str,
    error_code: str,
    message: str | None = None,
    severity: str = "ERROR",
    status: str = "OPEN",
    entity_type: str | None = None,
    entity_id: str | UUID | None = None,
    solver_run_id: str | UUID | None = None,
    user=None,
    affected_teacher: str | None = None,
    affected_class: str | None = None,
    affected_subject: str | None = None,
    resolution: str | None = None,
    details: dict[str, Any] | None = None,
):
    """
    Persist an exception in SmartTimeTable Error Center.

    ErrorRecord intentionally permits missing contextual information through
    empty strings because its contextual database fields are NULL=False and
    blank=True.

    The original exception is not swallowed by this function.
    """

    from apps.audit.models import ErrorRecord

    return ErrorRecord.objects.create(
        severity=_text(severity),
        status=_text(status),
        subsystem=_text(subsystem),
        operation=_text(operation),
        error_code=_text(error_code),
        message=_text(message) or str(exception),
        technical_exception=(
            f"{type(exception).__module__}."
            f"{type(exception).__name__}"
        ),
        traceback="".join(
            traceback.format_exception(
                type(exception),
                exception,
                exception.__traceback__,
            )
        ),
        entity_type=_text(entity_type),
        entity_id=_text(entity_id),
        affected_teacher=_text(affected_teacher),
        affected_class=_text(affected_class),
        affected_subject=_text(affected_subject),
        solver_run_id=_text(solver_run_id),
        resolution=_text(resolution),
        details=details if details is not None else {},
        user=user,
    )
