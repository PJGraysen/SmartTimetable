from __future__ import annotations

from .models import ErrorSeverity, ErrorStatus


VALID_ERROR_SEVERITIES = {
    choice for choice, _ in ErrorSeverity.choices
}

VALID_ERROR_STATUSES = {
    choice for choice, _ in ErrorStatus.choices
}


def validate_error_payload(
    *,
    severity: str,
    status: str,
    subsystem: str,
    operation: str,
    error_code: str,
    message: str,
) -> None:
    """Validate the minimum operational Error Center payload."""

    if severity not in VALID_ERROR_SEVERITIES:
        raise ValueError(f"Invalid error severity: {severity}")

    if status not in VALID_ERROR_STATUSES:
        raise ValueError(f"Invalid error status: {status}")

    required = {
        "subsystem": subsystem,
        "operation": operation,
        "error_code": error_code,
        "message": message,
    }

    missing = [
        name
        for name, value in required.items()
        if not str(value).strip()
    ]

    if missing:
        raise ValueError(
            "Error record is missing required fields: "
            + ", ".join(missing)
        )
