from __future__ import annotations

from apps.scheduling.engine.validation.result import (
    ValidationFinding,
    ValidationSummary,
)


def test_validation_summary_is_valid_without_errors():
    summary = ValidationSummary(
        findings=(
            ValidationFinding(
                severity="WARNING",
                category="OTHER",
                message="Example warning.",
            ),
        )
    )

    assert summary.is_valid is True
    assert summary.error_count == 0
    assert summary.warning_count == 1
    assert summary.info_count == 0
    assert summary.total_count == 1


def test_validation_summary_is_invalid_with_error():
    summary = ValidationSummary(
        findings=(
            ValidationFinding(
                severity="ERROR",
                category="TEACHER_CLASH",
                message="Teacher has a clash.",
            ),
        )
    )

    assert summary.is_valid is False
    assert summary.error_count == 1
    assert summary.warning_count == 0
    assert summary.info_count == 0
    assert summary.total_count == 1


def test_validation_summary_counts_multiple_severities():
    summary = ValidationSummary(
        findings=(
            ValidationFinding(
                severity="ERROR",
                category="TEACHER_CLASH",
                message="Teacher clash.",
            ),
            ValidationFinding(
                severity="ERROR",
                category="ROOM_CLASH",
                message="Room clash.",
            ),
            ValidationFinding(
                severity="WARNING",
                category="OTHER",
                message="Warning.",
            ),
            ValidationFinding(
                severity="INFO",
                category="OTHER",
                message="Information.",
            ),
        )
    )

    assert summary.error_count == 2
    assert summary.warning_count == 1
    assert summary.info_count == 1
    assert summary.total_count == 4
    assert summary.is_valid is False


def test_validation_finding_preserves_context():
    finding = ValidationFinding(
        severity="ERROR",
        category="FREE_AFTERNOON_VIOLATION",
        message="Teacher is scheduled during their free afternoon.",
        details={"period_part": "AFTERNOON"},
        teacher_id="teacher-1",
        instructional_group_id="group-1",
        period_id="period-5",
        day="MON",
        room_id="room-1",
        timetable_entry_id="entry-1",
    )

    assert finding.teacher_id == "teacher-1"
    assert finding.instructional_group_id == "group-1"
    assert finding.period_id == "period-5"
    assert finding.day == "MON"
    assert finding.room_id == "room-1"
    assert finding.timetable_entry_id == "entry-1"
    assert finding.details["period_part"] == "AFTERNOON"
