from datetime import time
from uuid import uuid4

from apps.scheduling.engine.domain.entities import (
    InstructionalGroupEntity,
    LessonRequirementEntity,
    PeriodEntity,
    RoomAvailabilityEntity,
    RoomEntity,
    TeacherAssignmentEntity,
    TeacherAvailabilityEntity,
    TeacherEntity,
    TeacherFreeAfternoonEntity,
    TimetableSlot,
)
from apps.scheduling.engine.domain.enums import (
    DayOfWeek,
    PartOfDay,
)
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.infeasibility_diagnostics import (
    analyze_infeasibility,
)


def build_problem(
    *,
    periods_per_week=1,
    teacher_assignment=True,
    teacher_available=True,
    room_available=True,
    teacher_free_afternoon=DayOfWeek.WEDNESDAY,
    teaching_period_count=2,
    room_count=1,
):
    teacher_id = uuid4()
    group_id = uuid4()
    requirement_id = uuid4()

    period_ids = [
        uuid4()
        for _ in range(teaching_period_count)
    ]

    periods = tuple(
        PeriodEntity(
            id=period_id,
            number=index + 1,
            name=f"Period {index + 1}",
            start_time=time(8 + index, 0),
            end_time=time(8 + index, 40),
            part_of_day=(
                PartOfDay.MORNING
                if index == 0
                else PartOfDay.AFTERNOON
            ),
            is_teaching_period=True,
        )
        for index, period_id in enumerate(period_ids)
    )

    teacher = TeacherEntity(
        id=teacher_id,
        name="Test Teacher",
        code="T001",
    )

    group = InstructionalGroupEntity(
        id=group_id,
        name="Test Group",
        code="G001",
    )

    rooms = tuple(
        RoomEntity(
            id=uuid4(),
            name=f"Test Room {index + 1}",
            code=f"R{index + 1:03d}",
            capacity=50,
        )
        for index in range(room_count)
    )

    requirement = LessonRequirementEntity(
        id=requirement_id,
        instructional_group_id=group_id,
        subject_id=uuid4(),
        periods_per_week=periods_per_week,
    )

    assignments = (
        (
            TeacherAssignmentEntity(
                id=uuid4(),
                teacher_id=teacher_id,
                lesson_requirement_id=requirement_id,
            ),
        )
        if teacher_assignment
        else ()
    )

    teacher_availability = tuple(
        TeacherAvailabilityEntity(
            id=uuid4(),
            teacher_id=teacher_id,
            day=(
                DayOfWeek.MONDAY
                if index == 0
                else DayOfWeek.TUESDAY
            ),
            period_id=period_id,
            is_available=teacher_available,
        )
        for index, period_id in enumerate(period_ids)
    )

    room_availability = tuple(
        RoomAvailabilityEntity(
            id=uuid4(),
            room_id=room.id,
            day=(
                DayOfWeek.MONDAY
                if index == 0
                else DayOfWeek.TUESDAY
            ),
            period_id=period_id,
            is_available=room_available,
        )
        for room in rooms
        for index, period_id in enumerate(period_ids)
    )

    free_afternoons = (
        TeacherFreeAfternoonEntity(
            id=uuid4(),
            teacher_id=teacher_id,
            day=teacher_free_afternoon,
        ),
    )

    slots = tuple(
        TimetableSlot(
            day=(
                DayOfWeek.MONDAY
                if index == 0
                else DayOfWeek.TUESDAY
            ),
            period_id=period_id,
            period_number=index + 1,
            part_of_day=(
                PartOfDay.MORNING
                if index == 0
                else PartOfDay.AFTERNOON
            ),
        )
        for index, period_id in enumerate(period_ids)
    )

    return SchedulingProblem.from_iterables(
        periods=periods,
        teachers=(teacher,),
        instructional_groups=(group,),
        rooms=rooms,
        lesson_requirements=(requirement,),
        teacher_assignments=assignments,
        teacher_availability=teacher_availability,
        teacher_free_afternoons=free_afternoons,
        room_availability=room_availability,
        slots=slots,
    )


def build_grade10_parallel_problem():
    group_id = uuid4()
    teacher_id = uuid4()
    room_id = uuid4()

    period_ids = [uuid4() for _ in range(10)]

    periods = tuple(
        PeriodEntity(
            id=period_id,
            number=index + 1,
            name=f"Period {index + 1}",
            start_time=time(8 + (index % 4), 0),
            end_time=time(8 + (index % 4), 40),
            part_of_day=(
                PartOfDay.MORNING
                if index < 5
                else PartOfDay.AFTERNOON
            ),
            is_teaching_period=True,
        )
        for index, period_id in enumerate(period_ids)
    )

    days = (
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    )

    slots = tuple(
        TimetableSlot(
            day=day,
            period_id=period_id,
            period_number=index + 1,
            part_of_day=(
                PartOfDay.MORNING
                if index < 5
                else PartOfDay.AFTERNOON
            ),
        )
        for day in days
        for period_id, index in zip(period_ids, range(10))
    )

    group = InstructionalGroupEntity(
        id=group_id,
        name="Grade 10E",
        code="10E",
    )

    teacher = TeacherEntity(
        id=teacher_id,
        name="Grade 10 Teacher",
        code="T010",
    )

    room = RoomEntity(
        id=room_id,
        name="Grade 10 Room",
        code="R010",
        capacity=50,
    )

    core_codes = {
        "ENG": 5,
        "KIS": 5,
        "EMCM": 5,
        "CRE": 4,
        "CSL": 3,
        "ICT": 2,
        "PE": 3,
        "PRP": 1,
        "GST": 1,
    }

    option_codes = {
        "BIO": 5,
        "MUS": 5,
        "FRE": 5,
        "CHEM": 5,
        "PHY": 5,
        "LIT": 5,
        "GEO": 5,
        "HIS": 5,
        "CS": 5,
        "BUS": 5,
        "AGR": 5,
    }

    requirements = []

    for code, frequency in {
        **core_codes,
        **option_codes,
    }.items():
        requirements.append(
            LessonRequirementEntity(
                id=uuid4(),
                instructional_group_id=group_id,
                subject_id=uuid4(),
                periods_per_week=frequency,
                subject_code=code,
            )
        )

    return SchedulingProblem.from_iterables(
        periods=periods,
        teachers=(teacher,),
        instructional_groups=(group,),
        rooms=(room,),
        lesson_requirements=tuple(requirements),
        teacher_assignments=(),
        teacher_availability=(),
        teacher_free_afternoons=(),
        room_availability=(),
        slots=slots,
    )


def test_missing_teacher_assignment_is_not_reported_as_infeasibility():
    problem = build_problem(
        teacher_assignment=False,
    )

    report = analyze_infeasibility(problem)

    codes = {
        diagnostic.code
        for diagnostic in report.diagnostics
    }

    assert "MISSING_ACTIVE_TEACHER_ASSIGNMENT" not in codes


def test_teacher_unavailability_can_make_requirement_infeasible():
    problem = build_problem(
        periods_per_week=1,
        teacher_available=False,
    )

    report = analyze_infeasibility(problem)

    codes = {
        diagnostic.code
        for diagnostic in report.diagnostics
    }

    assert "LESSON_SLOT_CAPACITY" in codes


def test_room_unavailability_can_make_requirement_infeasible():
    problem = build_problem(
        periods_per_week=1,
        room_available=False,
    )

    report = analyze_infeasibility(problem)

    codes = {
        diagnostic.code
        for diagnostic in report.diagnostics
    }

    assert "LESSON_SLOT_CAPACITY" in codes


def test_weekly_requirement_above_available_slots_is_reported():
    problem = build_problem(
        periods_per_week=3,
        teaching_period_count=2,
    )

    report = analyze_infeasibility(problem)

    codes = {
        diagnostic.code
        for diagnostic in report.diagnostics
    }

    assert "LESSON_SLOT_CAPACITY" in codes


def test_room_capacity_is_reported_when_total_room_slots_are_insufficient():
    problem = build_problem(
        periods_per_week=3,
        teaching_period_count=2,
        room_count=1,
    )

    report = analyze_infeasibility(problem)

    codes = {
        diagnostic.code
        for diagnostic in report.diagnostics
    }

    assert "ROOM_CAPACITY" in codes


def test_multiple_rooms_increase_room_slot_capacity():
    problem = build_problem(
        periods_per_week=2,
        teaching_period_count=2,
        room_count=2,
    )

    report = analyze_infeasibility(problem)

    codes = {
        diagnostic.code
        for diagnostic in report.diagnostics
    }

    assert "ROOM_CAPACITY" not in codes


def test_rooms_are_loaded_into_scheduling_problem():
    problem = build_problem(
        room_count=2,
    )

    assert len(problem.rooms) == 2
    assert all(room.is_active for room in problem.rooms)

    room_ids = {
        room.id
        for room in problem.rooms
    }

    assert len(room_ids) == 2


def test_room_availability_is_loaded_for_every_room_and_period():
    problem = build_problem(
        room_count=2,
        teaching_period_count=2,
    )

    expected_count = 2 * 2

    assert len(problem.room_availability) == expected_count

    room_ids = {
        room.id
        for room in problem.rooms
    }

    loaded_room_ids = {
        availability.room_id
        for availability in problem.room_availability
    }

    assert loaded_room_ids == room_ids


def test_diagnostic_message_contains_required_input():
    problem = build_problem(
        periods_per_week=3,
        teaching_period_count=2,
    )

    report = analyze_infeasibility(problem)
    message = report.format_message()

    assert "TIMETABLE GENERATION FAILED" in message
    assert "Required input:" in message
    assert "Weekly lesson requirement capacity" in message


def test_inactive_instructional_group_is_reported():
    problem = build_problem()

    group = problem.instructional_groups[0]

    inactive_group = InstructionalGroupEntity(
        id=group.id,
        name=group.name,
        code=group.code,
        is_active=False,
    )

    problem = SchedulingProblem.from_iterables(
        periods=problem.periods,
        teachers=problem.teachers,
        instructional_groups=(inactive_group,),
        rooms=problem.rooms,
        lesson_requirements=problem.lesson_requirements,
        teacher_assignments=problem.teacher_assignments,
        teacher_availability=problem.teacher_availability,
        teacher_free_afternoons=problem.teacher_free_afternoons,
        room_availability=problem.room_availability,
        slots=problem.slots,
    )

    report = analyze_infeasibility(problem)

    codes = {
        diagnostic.code
        for diagnostic in report.diagnostics
    }

    assert "INACTIVE_INSTRUCTIONAL_GROUP" in codes


def test_teacher_free_afternoon_is_loaded_and_preserved():
    problem = build_problem(
        teacher_free_afternoon=DayOfWeek.WEDNESDAY,
    )

    assert len(problem.teacher_free_afternoons) == 1

    assignment = problem.teacher_free_afternoons[0]

    assert assignment.teacher_id == problem.teachers[0].id
    assert assignment.day == DayOfWeek.WEDNESDAY


def test_room_diagnostics_include_room_names():
    problem = build_problem(
        periods_per_week=3,
        teaching_period_count=2,
        room_count=2,
    )

    unavailable_room_availability = tuple(
        RoomAvailabilityEntity(
            id=availability.id,
            room_id=availability.room_id,
            day=availability.day,
            period_id=availability.period_id,
            is_available=False,
        )
        for availability in problem.room_availability
    )

    problem = SchedulingProblem.from_iterables(
        periods=problem.periods,
        teachers=problem.teachers,
        instructional_groups=problem.instructional_groups,
        rooms=problem.rooms,
        lesson_requirements=problem.lesson_requirements,
        teacher_assignments=problem.teacher_assignments,
        teacher_availability=problem.teacher_availability,
        teacher_free_afternoons=problem.teacher_free_afternoons,
        room_availability=unavailable_room_availability,
        slots=problem.slots,
    )

    report = analyze_infeasibility(problem)

    room_capacity_diagnostics = [
        diagnostic
        for diagnostic in report.diagnostics
        if diagnostic.code == "ROOM_CAPACITY"
    ]

    assert room_capacity_diagnostics

    diagnostic = room_capacity_diagnostics[0]

    assert "R001" in diagnostic.details["rooms"]
    assert "R002" in diagnostic.details["rooms"]


def test_grade10_parallel_electives_count_as_shared_physical_slots():
    problem = build_grade10_parallel_problem()

    report = analyze_infeasibility(problem)

    capacity_diagnostics = [
        diagnostic
        for diagnostic in report.diagnostics
        if diagnostic.code == "INSTRUCTIONAL_GROUP_CAPACITY"
    ]

    assert not capacity_diagnostics


def test_grade10_effective_demand_is_49_not_84():
    problem = build_grade10_parallel_problem()

    report = analyze_infeasibility(problem)

    capacity_diagnostics = [
        diagnostic
        for diagnostic in report.diagnostics
        if diagnostic.code == "INSTRUCTIONAL_GROUP_CAPACITY"
    ]

    assert not capacity_diagnostics