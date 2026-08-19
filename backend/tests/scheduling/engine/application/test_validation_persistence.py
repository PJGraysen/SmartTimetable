from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.core.models import AcademicYear, School, Term
from apps.scheduling.models import (
SchedulingRun,
SchedulingRunStatus,
ValidationResult,
)
from apps.scheduling.engine.application.validation_persistence import (
ValidationPersistenceError,
clear_validation_results,
persist_validation_findings,
persist_validation_summary,
)
from apps.scheduling.engine.domain.enums import (
ValidationCategory,
ValidationSeverity,
)

# ---------------------------------------------------------------------------

# Database fixture helpers

# ---------------------------------------------------------------------------

@pytest.fixture
def scheduling_run(db):
    school = School.objects.create(
        name="Test School",
        code="TEST",
    )

    academic_year = AcademicYear.objects.create(
    school=school,
    name="2026",
    start_date="2026-01-01",
    end_date="2026-12-31",
    )

    term = Term.objects.create(
        academic_year=academic_year,
        name="Term 1",
        number=1,
        start_date="2026-01-01",
        end_date="2026-04-30",
    )

    return SchedulingRun.objects.create(
        term=term,
        status=SchedulingRunStatus.RUNNING,
    )

# ---------------------------------------------------------------------------

# Validation finding helpers

# ---------------------------------------------------------------------------

def make_finding(
*,
severity=ValidationSeverity.ERROR,
category=ValidationCategory.TEACHER_CLASH,
message="Test validation finding.",
context=None,
):
    return SimpleNamespace(
        severity=severity,
        category=category,
        message=message,
        context={} if context is None else context,
    )

def make_summary(findings):
    return SimpleNamespace(
        findings=tuple(findings),
    )

# ---------------------------------------------------------------------------

# Persist validation findings

# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_persist_validation_findings_creates_database_records(
    scheduling_run,
):
    findings = (
        make_finding(
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.TEACHER_CLASH,
            message="Teacher clash detected.",
            context={"teacher_id": "teacher-1"},
        ),
        make_finding(
            severity=ValidationSeverity.WARNING,
            category="OTHER",
            message="Test warning.",
            context={"source": "test"},
        ),
    )

    persisted = persist_validation_findings(
        scheduling_run,
        findings,
    )

    assert len(persisted) == 2
    assert ValidationResult.objects.filter(
        scheduling_run=scheduling_run
    ).count() == 2

    first = ValidationResult.objects.get(
        scheduling_run=scheduling_run,
        message="Teacher clash detected.",
    )

    assert first.severity == ValidationSeverity.ERROR.value
    assert first.category == ValidationCategory.TEACHER_CLASH.value
    assert first.details == {"teacher_id": "teacher-1"}

@pytest.mark.django_db
def test_persist_validation_findings_handles_empty_findings(
scheduling_run,
):
    persisted = persist_validation_findings(
        scheduling_run,
        (),
    )

    assert persisted == ()
    assert ValidationResult.objects.filter(
        scheduling_run=scheduling_run
    ).count() == 0


@pytest.mark.django_db
def test_persist_validation_findings_clears_old_findings(
    scheduling_run,
):
    old_finding = make_finding(
        message="Old finding.",
    )

    persist_validation_findings(
        scheduling_run,
        (old_finding,),
    )

    assert ValidationResult.objects.filter(
        scheduling_run=scheduling_run
    ).count() == 1

    new_findings = (
        make_finding(
            message="New finding one.",
        ),
        make_finding(
            message="New finding two.",
        ),
    )

    persisted = persist_validation_findings(
        scheduling_run,
        new_findings,
    )

    assert len(persisted) == 2

    results = ValidationResult.objects.filter(
        scheduling_run=scheduling_run
    )

    assert results.count() == 2
    assert not results.filter(message="Old finding.").exists()
    assert results.filter(message="New finding one.").exists()
    assert results.filter(message="New finding two.").exists()


@pytest.mark.django_db
def test_persist_validation_findings_accepts_generators(
    scheduling_run,
):
    findings = (
        make_finding(message=f"Finding {index}.")
        for index in range(3)
    )

    persisted = persist_validation_findings(
        scheduling_run,
        findings,
    )

    assert len(persisted) == 3
    assert ValidationResult.objects.filter(
        scheduling_run=scheduling_run
    ).count() == 3

# ---------------------------------------------------------------------------

# Persist validation summary

# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_persist_validation_summary_uses_summary_findings(
    scheduling_run,
):
    findings = (
        make_finding(
            message="Summary finding one.",
        ),
        make_finding(
            message="Summary finding two.",
        ),
    )

    summary = make_summary(findings)

    persisted = persist_validation_summary(
        scheduling_run,
        summary,
    )

    assert len(persisted) == 2

    assert ValidationResult.objects.filter(
        scheduling_run=scheduling_run,
        message="Summary finding one.",
    ).exists()

    assert ValidationResult.objects.filter(
        scheduling_run=scheduling_run,
        message="Summary finding two.",
    ).exists()


@pytest.mark.django_db
def test_persist_validation_summary_rejects_none(
    scheduling_run,
):
    with pytest.raises(
        ValidationPersistenceError,
    ):
        persist_validation_summary(
            scheduling_run,
            None,
        )

# ---------------------------------------------------------------------------

# Clear validation results

# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_clear_validation_results_removes_all_results(
    scheduling_run,
):
    findings = (
        make_finding(message="Finding one."),
        make_finding(message="Finding two."),
        make_finding(message="Finding three."),
    )

    persist_validation_findings(
        scheduling_run,
        findings,
    )

    assert ValidationResult.objects.filter(
        scheduling_run=scheduling_run
    ).count() == 3

    deleted_count = clear_validation_results(
        scheduling_run,
    )

    assert deleted_count == 3

    assert ValidationResult.objects.filter(
        scheduling_run=scheduling_run
    ).count() == 0

# ---------------------------------------------------------------------------

# Unsaved SchedulingRun protection

# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_persistence_rejects_unsaved_scheduling_run():
    scheduling_run = SchedulingRun()

    finding = make_finding(
        severity=ValidationSeverity.ERROR,
        category="OTHER",
        message="Test finding.",
    )

    with pytest.raises(
        ValidationPersistenceError,
    ):
        persist_validation_findings(
            scheduling_run,
            (finding,),
        )

    assert ValidationResult.objects.count() == 0