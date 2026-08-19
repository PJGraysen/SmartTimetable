from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationFinding:
    """
    Represents one timetable validation finding.

    This is a domain-level object. It deliberately does not depend on
    Django models so the validation engine remains independent of the
    persistence layer.
    """

    severity: str
    category: str
    message: str

    details: dict[str, Any] = field(default_factory=dict)

    teacher_id: str | None = None
    teaching_group_id: str | None = None
    period_id: str | None = None
    day: str | None = None
    room_id: str | None = None
    timetable_entry_id: str | None = None


@dataclass(frozen=True)
class ValidationSummary:
    """
    Aggregate result returned after validating a timetable.
    """

    findings: tuple[ValidationFinding, ...] = ()

    @property
    def error_count(self) -> int:
        return sum(
            finding.severity == "ERROR"
            for finding in self.findings
        )

    @property
    def warning_count(self) -> int:
        return sum(
            finding.severity == "WARNING"
            for finding in self.findings
        )

    @property
    def info_count(self) -> int:
        return sum(
            finding.severity == "INFO"
            for finding in self.findings
        )

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0

    @property
    def total_count(self) -> int:
        return len(self.findings)
