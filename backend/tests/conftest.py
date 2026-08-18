from __future__ import annotations

import pytest

from apps.core.models import AcademicYear, School, Term
from apps.scheduling.models import (
    SchedulingRun,
    SchedulingRunStatus,
)


@pytest.fixture
def scheduling_run():
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
        status=SchedulingRunStatus.PENDING,
    )