from __future__ import annotations

import pytest

from apps.academics.models import (
    Grade,
    LessonRequirement,
    Stream,
    Subject,
    TeachingGroup,
    InstructionalGroup,
)
from apps.core.models import AcademicYear, School, Term
from apps.scheduling.models import (
    SchedulingRun,
    SchedulingRunStatus,
)


@pytest.fixture
def school():
    return School.objects.create(
        name="Test School",
        code="TEST",
    )


@pytest.fixture
def academic_year(school):
    return AcademicYear.objects.create(
        school=school,
        name="2026",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_active=True,
    )


@pytest.fixture
def term(academic_year):
    return Term.objects.create(
        academic_year=academic_year,
        name="Term 1",
        number=1,
        start_date="2026-01-01",
        end_date="2026-04-30",
        is_active=True,
    )


@pytest.fixture
def grade(academic_year):
    return Grade.objects.create(
        academic_year=academic_year,
        name="Grade 10",
        code="G10",
    )


@pytest.fixture
def stream(grade):
    return Stream.objects.create(
        grade=grade,
        name="Stream A",
        code="A",
    )


@pytest.fixture
def teaching_group(stream):
    return TeachingGroup.objects.create(
        stream=stream,
        name="Grade 10 Stream A",
        code="G10A",
        learner_count=45,
        is_active=True,
    )


@pytest.fixture
def subject():
    return Subject.objects.create(
        name="Mathematics",
        code="MAT",
        is_active=True,
    )


@pytest.fixture
def instructional_group(teaching_group):
    return InstructionalGroup.objects.create(
        teaching_group=teaching_group,
        name="Core",
        code="G10A-CORE",
        learner_count=45,
        is_active=True,
    )


@pytest.fixture
def lesson_requirement(term, instructional_group, subject):
    return LessonRequirement.objects.create(
        term=term,
        instructional_group=instructional_group,
        subject=subject,
        lessons_per_week=4,
        is_active=True,
    )

@pytest.fixture
def scheduling_run():
    school = School.objects.create(
        name="Scheduling Test School",
        code="SCHED-TEST",
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
