from datetime import time
from uuid import uuid4

from apps.scheduling.engine.domain.entities import (
    LessonRequirementEntity,
    PeriodEntity,
    RoomEntity,
    RoomAvailabilityEntity,
    TeacherAssignmentEntity,
    TeacherEntity,
    TeacherFreeAfternoonEntity,
    InstructionalGroupEntity,
    TimetableSlot,
)
from apps.scheduling.engine.domain.enums import (
    DayOfWeek,
    PartOfDay,
    SolverStatus,
)
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver


def build_test_problem() -> SchedulingProblem:
    """Create a small deterministic scheduling problem."""

    teacher_id = uuid4()
    group_id = uuid4()
    room_id = uuid4()
    requirement_id = uuid4()
    assignment_id = uuid4()
    free_afternoon_id = uuid4()

    monday_period = uuid4()
    tuesday_period = uuid4()

    # Monday P1 is reserved for Assembly.
    # The integration fixture therefore uses Monday P2 and Tuesday P2.
    periods = (
        PeriodEntity(
            id=monday_period,
            number=2,
            name="Monday Period 2",
            start_time=time(8, 40),
            end_time=time(9, 20),
            part_of_day=PartOfDay.MORNING,
            is_teaching_period=True,
        ),
        PeriodEntity(
            id=tuesday_period,
            number=3,
            name="Tuesday Period 3",
            start_time=time(9, 20),
            end_time=time(10, 0),
            part_of_day=PartOfDay.MORNING,
            is_teaching_period=True,
        ),
    )

    teachers = (
        TeacherEntity(
            id=teacher_id,
            name="Test Teacher",
            code="T001",
        ),
    )

    instructional_groups = (
        InstructionalGroupEntity(
            id=group_id,
            name="Test Group",
            code="G001",
        ),
    )

    rooms = (
        RoomEntity(
            id=room_id,
            name="Test Room",
            code="R001",
            capacity=50,
        ),
    )

    lesson_requirements = (
        LessonRequirementEntity(
            id=requirement_id,
            instructional_group_id=group_id,
            subject_id=uuid4(),
            periods_per_week=2,
        ),
    )

    teacher_assignments = (
        TeacherAssignmentEntity(
            id=assignment_id,
            teacher_id=teacher_id,
            lesson_requirement_id=requirement_id,
        ),
    )

    teacher_free_afternoons = (
        TeacherFreeAfternoonEntity(
            id=free_afternoon_id,
            teacher_id=teacher_id,
            day=DayOfWeek.MONDAY,
        ),
    )

    room_availability = (
        RoomAvailabilityEntity(
            id=uuid4(),
            room_id=room_id,
            day=DayOfWeek.MONDAY,
            period_id=monday_period,
            is_available=True,
        ),
        RoomAvailabilityEntity(
            id=uuid4(),
            room_id=room_id,
            day=DayOfWeek.TUESDAY,
            period_id=tuesday_period,
            is_available=True,
        ),
    )

    slots = (
        TimetableSlot(
            day=DayOfWeek.MONDAY,
            period_id=monday_period,
            period_number=2,
            part_of_day=PartOfDay.MORNING,
        ),
        TimetableSlot(
            day=DayOfWeek.TUESDAY,
            period_id=tuesday_period,
            period_number=3,
            part_of_day=PartOfDay.MORNING,
        ),
    )

    return SchedulingProblem.from_iterables(
        periods=periods,
        teachers=teachers,
        instructional_groups=instructional_groups,
        rooms=rooms,
        lesson_requirements=lesson_requirements,
        teacher_assignments=teacher_assignments,
        teacher_availability=(),
        teacher_free_afternoons=teacher_free_afternoons,
        room_availability=room_availability,
        slots=slots,
    )


def test_solver_generates_feasible_timetable():
    """The solver should generate all required lesson periods."""

    problem = build_test_problem()

    solver_model = SolverModelBuilder().build(problem)

    result = CPSATSolver(
        time_limit_seconds=10.0,
        num_workers=1,
    ).solve(
        problem=problem,
        solver_model=solver_model,
    )

    assert result.status in {
        SolverStatus.FEASIBLE,
        SolverStatus.OPTIMAL,
    }

    assert result.is_successful

    assert len(result.assignments) == 2

    requirement_id = problem.lesson_requirements[0].id

    assert all(
        assignment.lesson_requirement_id == requirement_id
        for assignment in result.assignments
    )


def test_solver_respects_teacher_free_afternoon():
    """The solver must never schedule a teacher during their free afternoon."""

    problem = build_test_problem()

    solver_model = SolverModelBuilder().build(problem)

    result = CPSATSolver(
        time_limit_seconds=10.0,
        num_workers=1,
    ).solve(
        problem=problem,
        solver_model=solver_model,
    )

    assert result.is_successful

    teacher_id = problem.teachers[0].id
    free_afternoon = problem.teacher_free_afternoon(teacher_id)

    assert free_afternoon is not None

    for assignment in result.assignments:
        assert not problem.is_teacher_free_afternoon(
            teacher_id=assignment.teacher_id,
            day=assignment.day,
            period_id=assignment.period_id,
        )