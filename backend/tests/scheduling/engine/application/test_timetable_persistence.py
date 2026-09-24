from uuid import uuid4

import pytest

from apps.scheduling.engine.application.timetable_persistence import (
    TimetablePersistenceService,
)
from apps.scheduling.engine.domain.entities import SchedulingAssignment
from apps.scheduling.engine.domain.enums import DayOfWeek, SolverStatus
from apps.scheduling.engine.solver.result import (
    SolverResult,
    SolverStatistics,
)
from apps.academics.models import (
    InstructionalGroup,
    Grade,
    LessonRequirement,
    Stream,
    Subject,
    TeachingGroup,
)
from apps.core.models import AcademicYear, School, Term
from apps.scheduling.models import (
    Period,
    Room,
    SchedulingRun,
    SchedulingRunStatus,
    TeacherAssignment,
    TimetableEntry,
    TimetableVersion,
)
from apps.users.models import Teacher
from django.contrib.auth.models import User


@pytest.fixture
def scheduling_data():
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

    grade = Grade.objects.create(
        academic_year=academic_year,
        name="Grade 10",
        code="G10",
    )

    stream = Stream.objects.create(
        grade=grade,
        name="A",
        code="A",
    )

    group = TeachingGroup.objects.create(
        stream=stream,
        name="Grade 10A",
        code="G10A",
        learner_count=45,
    )


    instructional_group = InstructionalGroup.objects.create(
        teaching_group=group,
        name=group.name,
        code=group.code,
        learner_count=group.learner_count,
        is_active=group.is_active,
    )

    subject = Subject.objects.create(
        name="Computer Science",
        code="CS",
    )

    requirement = LessonRequirement.objects.create(
        term=term,
        instructional_group=instructional_group,
        subject=subject,
        lessons_per_week=1,
        is_active=True,
    )

    user = User.objects.create_user(
        username="teacher001",
    )

    teacher = Teacher.objects.create(
        user=user,
        employee_code="EMP001",
        first_name="John",
        last_name="Teacher",
        is_active=True,
    )

    TeacherAssignment.objects.create(
        teacher=teacher,
        lesson_requirement=requirement,
        is_active=True,
    )

    period = Period.objects.create(
        name="Monday Period 1",
        number=1,
        start_time="08:00",
        end_time="08:40",
        is_teaching_period=True,
        part_of_day="MORNING",
        is_active=True,
    )

    room = Room.objects.create(
        school=school,
        name="Computer Laboratory",
        code="LAB1",
        capacity=45,
        is_active=True,
    )

    run = SchedulingRun.objects.create(
        term=term,
        status=SchedulingRunStatus.RUNNING,
    )

    return {
        "term": term,
        "group": group,
        "instructional_group": instructional_group,
        "requirement": requirement,
        "teacher": teacher,
        "period": period,
        "room": room,
        "run": run,
    }


@pytest.mark.django_db
def test_persist_creates_timetable_version_and_entries(
    scheduling_data,
):
    data = scheduling_data

    assignment = SchedulingAssignment(
        lesson_requirement_id=data["requirement"].id,
        teacher_id=data["teacher"].id,
        instructional_group_id=data["instructional_group"].id,
        period_id=data["period"].id,
        day=DayOfWeek.MONDAY,
        room_id=data["room"].id,
    )

    result = SolverResult(
        status=SolverStatus.OPTIMAL,
        assignments=(assignment,),
        statistics=SolverStatistics(
            wall_time_seconds=1.25,
            branches=10,
            conflicts=2,
            objective_value=100.0,
        ),
    )

    persistence_result = TimetablePersistenceService().persist(
        scheduling_run=data["run"],
        solver_result=result,
        version_name="Generated Timetable",
        version_number=1,
    )

    assert persistence_result.entries_created == 1

    version = persistence_result.timetable_version

    assert version.term_id == data["term"].id
    assert version.name == "Generated Timetable"
    assert version.version_number == 1
    assert version.is_published is False
    assert version.is_active is True

    entry = TimetableEntry.objects.get(
        timetable_version=version,
    )

    assert entry.day == "MON"
    assert entry.period_id == data["period"].id
    assert entry.instructional_group_id == data["instructional_group"].id
    assert entry.teacher_id == data["teacher"].id
    assert entry.lesson_requirement_id == data["requirement"].id
    assert entry.room_id == data["room"].id

    data["run"].refresh_from_db()

    assert data["run"].status == SchedulingRunStatus.COMPLETED
    assert data["run"].solver_status == "OPTIMAL"
    assert data["run"].completed_at is not None
    assert data["run"].statistics["entries_created"] == 1
    assert data["run"].statistics["branches"] == 10
    assert data["run"].statistics["conflicts"] == 2


@pytest.mark.django_db
def test_persist_resolves_existing_version_number(
    scheduling_data,
):
    data = scheduling_data

    assignment = SchedulingAssignment(
        lesson_requirement_id=data["requirement"].id,
        teacher_id=data["teacher"].id,
        instructional_group_id=data["instructional_group"].id,
        period_id=data["period"].id,
        day=DayOfWeek.MONDAY,
        room_id=data["room"].id,
    )

    result = SolverResult(
        status=SolverStatus.OPTIMAL,
        assignments=(assignment,),
        statistics=SolverStatistics(
            wall_time_seconds=0.1,
            branches=0,
            conflicts=0,
            objective_value=0.0,
        ),
    )

    first_result = TimetablePersistenceService().persist(
        scheduling_run=data["run"],
        solver_result=result,
        version_name="First Timetable",
        version_number=1,
    )

    assert first_result.timetable_version.version_number == 1

    second_run = SchedulingRun.objects.create(
        term=data["term"],
        status=SchedulingRunStatus.RUNNING,
    )

    second_result = TimetablePersistenceService().persist(
        scheduling_run=second_run,
        solver_result=result,
        version_name="Second Timetable",
        version_number=1,
    )

    assert second_result.timetable_version.version_number == 2

    versions = list(
        TimetableVersion.objects.filter(
            term=data["term"],
        )
        .order_by("version_number")
        .values_list("version_number", "name")
    )

    assert versions == [
        (1, "First Timetable"),
        (2, "Second Timetable"),
    ]


@pytest.mark.django_db
def test_persist_accepts_feasible_result(
    scheduling_data,
):
    data = scheduling_data

    assignment = SchedulingAssignment(
        lesson_requirement_id=data["requirement"].id,
        teacher_id=data["teacher"].id,
        instructional_group_id=data["instructional_group"].id,
        period_id=data["period"].id,
        day=DayOfWeek.MONDAY,
    )

    result = SolverResult(
        status=SolverStatus.FEASIBLE,
        assignments=(assignment,),
    )

    persistence_result = TimetablePersistenceService().persist(
        scheduling_run=data["run"],
        solver_result=result,
        version_name="Feasible Timetable",
        version_number=1,
    )

    assert persistence_result.entries_created == 1

    data["run"].refresh_from_db()

    assert data["run"].status == SchedulingRunStatus.COMPLETED
    assert data["run"].solver_status == "FEASIBLE"


@pytest.mark.django_db
def test_persist_rejects_unsuccessful_solver_result(
    scheduling_data,
):
    data = scheduling_data

    result = SolverResult(
        status=SolverStatus.INFEASIBLE,
    )

    with pytest.raises(ValueError, match="Only FEASIBLE or OPTIMAL"):
        TimetablePersistenceService().persist(
            scheduling_run=data["run"],
            solver_result=result,
            version_name="Invalid Timetable",
            version_number=1,
        )

    assert TimetableVersion.objects.count() == 0
    assert TimetableEntry.objects.count() == 0

    data["run"].refresh_from_db()

    assert data["run"].status == SchedulingRunStatus.RUNNING


@pytest.mark.django_db
def test_persist_rejects_invalid_run_state(
    scheduling_data,
):
    data = scheduling_data

    data["run"].status = SchedulingRunStatus.COMPLETED
    data["run"].save(update_fields=["status"])

    result = SolverResult(
        status=SolverStatus.OPTIMAL,
    )

    with pytest.raises(ValueError, match="PENDING or RUNNING"):
        TimetablePersistenceService().persist(
            scheduling_run=data["run"],
            solver_result=result,
            version_name="Invalid Run",
            version_number=1,
        )

    assert TimetableVersion.objects.count() == 0


@pytest.mark.django_db
def test_persist_rolls_back_version_when_entry_creation_fails(
    scheduling_data,
):
    data = scheduling_data

    invalid_assignment = SchedulingAssignment(
        lesson_requirement_id=uuid4(),
        teacher_id=data["teacher"].id,
        instructional_group_id=data["instructional_group"].id,
        period_id=data["period"].id,
        day=DayOfWeek.MONDAY,
    )

    result = SolverResult(
        status=SolverStatus.OPTIMAL,
        assignments=(invalid_assignment,),
    )

    with pytest.raises(Exception):
        TimetablePersistenceService().persist(
            scheduling_run=data["run"],
            solver_result=result,
            version_name="Should Roll Back",
            version_number=1,
        )

    assert TimetableVersion.objects.count() == 0
    assert TimetableEntry.objects.count() == 0

# ============================================================================
# P1 REGRESSION - teacher=None is schema-supported; non-None IDs still validated
# ============================================================================

@pytest.mark.django_db
def test_validate_assignments_allows_none_teacher(lesson_requirement):
    from datetime import time
    from types import SimpleNamespace
    from apps.scheduling.engine.application.timetable_persistence import (
        TimetablePersistenceService,
    )
    from apps.scheduling.models import Period

    period = Period.objects.first()
    if period is None:
        try:
            period = Period.objects.create(
                number=99, name="Test Period",
                start_time=time(8, 0), end_time=time(8, 40),
                part_of_day="MORNING",
                is_teaching_period=True, is_active=True,
            )
        except Exception as exc:
            pytest.skip(f"Cannot construct Period fixture: {exc}")

    assignment = SimpleNamespace(
        lesson_requirement_id=lesson_requirement.id,
        teacher_id=None,
        instructional_group_id=lesson_requirement.instructional_group_id,
        period_id=period.id,
    )
    TimetablePersistenceService._validate_assignments([assignment])


@pytest.mark.django_db
def test_validate_assignments_still_rejects_bogus_teacher(lesson_requirement):
    from datetime import time
    from types import SimpleNamespace
    from uuid import uuid4
    from apps.scheduling.engine.application.timetable_persistence import (
        TimetablePersistenceService,
    )
    from apps.scheduling.models import Period

    period = Period.objects.first()
    if period is None:
        try:
            period = Period.objects.create(
                number=99, name="Test Period",
                start_time=time(8, 0), end_time=time(8, 40),
                part_of_day="MORNING",
                is_teaching_period=True, is_active=True,
            )
        except Exception as exc:
            pytest.skip(f"Cannot construct Period fixture: {exc}")

    assignment = SimpleNamespace(
        lesson_requirement_id=lesson_requirement.id,
        teacher_id=uuid4(),
        instructional_group_id=lesson_requirement.instructional_group_id,
        period_id=period.id,
    )
    with pytest.raises(ValueError, match="unknown teacher"):
        TimetablePersistenceService._validate_assignments([assignment])


# ==========================================================================
# ==========================================================================
# P3 R1 - physical-cell persistence projection
# ==========================================================================

def _unsaved_version():
    # Unsaved model instance passes the FK isinstance check without DB.
    from apps.scheduling.models import TimetableVersion
    return TimetableVersion()


def test_p3_r1_collapses_same_physical_cell():
    from types import SimpleNamespace
    from apps.scheduling.engine.application.timetable_persistence import (
        TimetablePersistenceService,
    )

    def a(day, period_id, group_id, req_id, room_id):
        return SimpleNamespace(
            day=day, period_id=period_id, instructional_group_id=group_id,
            lesson_requirement_id=req_id, teacher_id=None, room_id=room_id,
        )

    entries = TimetablePersistenceService._build_entries(
        timetable_version=_unsaved_version(),
        assignments=[
            a("TUE", "P-5", "GRP-1", "REQ-Z", "ROOM-Z"),
            a("TUE", "P-5", "GRP-1", "REQ-A", "ROOM-A"),
            a("TUE", "P-5", "GRP-1", "REQ-M", "ROOM-M"),
        ],
    )

    assert len(entries) == 1
    assert str(entries[0].lesson_requirement_id) == "REQ-A"


def test_p3_r1_representative_is_minimum_requirement_id():
    from types import SimpleNamespace
    from apps.scheduling.engine.application.timetable_persistence import (
        TimetablePersistenceService,
    )

    def a(req_id):
        return SimpleNamespace(
            day="MON", period_id="P-1", instructional_group_id="GRP-1",
            lesson_requirement_id=req_id, teacher_id=None, room_id="R",
        )

    entries = TimetablePersistenceService._build_entries(
        timetable_version=_unsaved_version(),
        assignments=[a("REQ-C"), a("REQ-B"), a("REQ-A")],
    )

    assert len(entries) == 1
    assert str(entries[0].lesson_requirement_id) == "REQ-A"


def test_p3_r1_preserves_distinct_physical_cells():
    from types import SimpleNamespace
    from apps.scheduling.engine.application.timetable_persistence import (
        TimetablePersistenceService,
    )

    def a(day, period_id, req_id):
        return SimpleNamespace(
            day=day, period_id=period_id, instructional_group_id="GRP-1",
            lesson_requirement_id=req_id, teacher_id=None, room_id="R",
        )

    entries = TimetablePersistenceService._build_entries(
        timetable_version=_unsaved_version(),
        assignments=[
            a("MON", "P-1", "REQ-B"),
            a("MON", "P-2", "REQ-A"),
            a("TUE", "P-1", "REQ-C"),
        ],
    )

    assert len(entries) == 3
    keys = {(e.day, e.period_id, e.instructional_group_id) for e in entries}
    assert keys == {
        ("MON", "P-1", "GRP-1"),
        ("MON", "P-2", "GRP-1"),
        ("TUE", "P-1", "GRP-1"),
    }

# ==========================================================================
# P4-A - teacher-event de-duplication
# ==========================================================================

def test_p4a_teacher_event_dedup():
    from types import SimpleNamespace
    from uuid import uuid4
    from apps.scheduling.engine.application.timetable_persistence import (
        TimetablePersistenceService,
    )
    from apps.scheduling.models import TimetableVersion

    teacher = uuid4()
    grp_a, grp_b = uuid4(), uuid4()
    req_a, req_b = uuid4(), uuid4()

    def a(group_id, req_id):
        return SimpleNamespace(
            day="MON", period_id=uuid4(), instructional_group_id=group_id,
            lesson_requirement_id=req_id, teacher_id=teacher, room_id=uuid4(),
        )

    period = uuid4()

    def a2(group_id, req_id):
        return SimpleNamespace(
            day="MON", period_id=period, instructional_group_id=group_id,
            lesson_requirement_id=req_id, teacher_id=teacher, room_id=uuid4(),
        )

    entries = TimetablePersistenceService._build_entries(
        timetable_version=TimetableVersion(),
        assignments=[a2(grp_a, req_a), a2(grp_b, req_b)],
    )

    assert len(entries) == 2
    with_teacher = [e for e in entries if e.teacher_id is not None]
    without_teacher = [e for e in entries if e.teacher_id is None]
    assert len(with_teacher) == 1
    assert len(without_teacher) == 1
    assert with_teacher[0].teacher_id == teacher


def test_p4a_single_teacher_row_untouched():
    from types import SimpleNamespace
    from uuid import uuid4
    from apps.scheduling.engine.application.timetable_persistence import (
        TimetablePersistenceService,
    )
    from apps.scheduling.models import TimetableVersion

    teacher = uuid4()
    assignment = SimpleNamespace(
        day="MON", period_id=uuid4(), instructional_group_id=uuid4(),
        lesson_requirement_id=uuid4(), teacher_id=teacher, room_id=uuid4(),
    )
    entries = TimetablePersistenceService._build_entries(
        timetable_version=TimetableVersion(),
        assignments=[assignment],
    )
    assert len(entries) == 1
    assert entries[0].teacher_id == teacher


def test_p4a_different_teachers_same_slot_untouched():
    from types import SimpleNamespace
    from uuid import uuid4
    from apps.scheduling.engine.application.timetable_persistence import (
        TimetablePersistenceService,
    )
    from apps.scheduling.models import TimetableVersion

    period = uuid4()
    t1, t2 = uuid4(), uuid4()

    def a(group_id, req_id, teacher):
        return SimpleNamespace(
            day="MON", period_id=period, instructional_group_id=group_id,
            lesson_requirement_id=req_id, teacher_id=teacher, room_id=uuid4(),
        )

    entries = TimetablePersistenceService._build_entries(
        timetable_version=TimetableVersion(),
        assignments=[a(uuid4(), uuid4(), t1), a(uuid4(), uuid4(), t2)],
    )
    assert len(entries) == 2
    assert all(e.teacher_id is not None for e in entries)
