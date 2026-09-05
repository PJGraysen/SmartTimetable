from datetime import time
from uuid import uuid4

from apps.scheduling.engine.domain.entities import (
    LessonRequirementEntity,
    PeriodEntity,
    RoomAvailabilityEntity,
    RoomEntity,
    TeacherAssignmentEntity,
    TeacherAvailabilityEntity,
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


def solve_problem(problem: SchedulingProblem):
    """Build and solve a scheduling problem for constraint tests."""

    solver_model = SolverModelBuilder().build(problem)

    return CPSATSolver(
        time_limit_seconds=10.0,
        num_workers=1,
    ).solve(
        problem=problem,
        solver_model=solver_model,
    )


def build_constraint_problem(
    *,
    teacher_count: int = 2,
    group_count: int = 2,
    room_count: int = 2,
    periods_per_week: int = 1,
    slots=None,
    teacher_assignments=None,
    teacher_availability=(),
    teacher_free_afternoons=None,
    room_availability=None,
):
    """Build a small deterministic problem for hard-constraint tests."""

    teachers = tuple(
        TeacherEntity(
            id=uuid4(),
            name=f"Teacher {index + 1}",
            code=f"T{index + 1:03d}",
        )
        for index in range(teacher_count)
    )

    instructional_groups = tuple(
        InstructionalGroupEntity(
            id=uuid4(),
            name=f"Group {index + 1}",
            code=f"G{index + 1:03d}",
        )
        for index in range(group_count)
    )

    rooms = tuple(
        RoomEntity(
            id=uuid4(),
            name=f"Room {index + 1}",
            code=f"R{index + 1:03d}",
            capacity=50,
        )
        for index in range(room_count)
    )

    monday_period = uuid4()
    tuesday_period = uuid4()

    # Monday P1 is institutionally reserved for Assembly.
    # This generic fixture therefore uses ordinary teaching periods only.
    periods = (
        PeriodEntity(
            id=monday_period,
            number=2,
            name="Period 2",
            start_time=time(8, 40),
            end_time=time(9, 20),
            part_of_day=PartOfDay.MORNING,
            is_teaching_period=True,
        ),
        PeriodEntity(
            id=tuesday_period,
            number=2,
            name="Period 2",
            start_time=time(8, 40),
            end_time=time(9, 20),
            part_of_day=PartOfDay.MORNING,
            is_teaching_period=True,
        ),
    )

    requirements = tuple(
        LessonRequirementEntity(
            id=uuid4(),
            instructional_group_id=group.id,
            subject_id=uuid4(),
            periods_per_week=periods_per_week,
        )
        for group in instructional_groups
    )

    if teacher_assignments is None:
        teacher_assignments = tuple(
            TeacherAssignmentEntity(
                id=uuid4(),
                teacher_id=teachers[index % len(teachers)].id,
                lesson_requirement_id=requirement.id,
            )
            for index, requirement in enumerate(requirements)
        )

    if slots is None:
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
                period_number=2,
                part_of_day=PartOfDay.MORNING,
            ),
        )

    if teacher_free_afternoons is None:
        teacher_free_afternoons = tuple(
            TeacherFreeAfternoonEntity(
                id=uuid4(),
                teacher_id=teacher.id,
                day=DayOfWeek.FRIDAY,
            )
            for teacher in teachers
        )

    if room_availability is None:
        room_availability = tuple(
            RoomAvailabilityEntity(
                id=uuid4(),
                room_id=room.id,
                day=slot.day,
                period_id=slot.period_id,
                is_available=True,
            )
            for room in rooms
            for slot in slots
        )

    return SchedulingProblem.from_iterables(
        periods=periods,
        teachers=teachers,
        instructional_groups=instructional_groups,
        rooms=rooms,
        lesson_requirements=requirements,
        teacher_assignments=teacher_assignments,
        teacher_availability=teacher_availability,
        teacher_free_afternoons=teacher_free_afternoons,
        room_availability=room_availability,
        slots=slots,
    )


def test_teacher_clash_is_prevented():
    """Two lessons cannot use the same teacher in the same slot."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=2,
        room_count=2,
    )

    teacher_id = problem.teachers[0].id

    teacher_assignments = tuple(
        TeacherAssignmentEntity(
            id=uuid4(),
            teacher_id=teacher_id,
            lesson_requirement_id=requirement.id,
        )
        for requirement in problem.lesson_requirements
    )

    problem = SchedulingProblem.from_iterables(
        periods=problem.periods,
        teachers=problem.teachers,
        instructional_groups=problem.instructional_groups,
        rooms=problem.rooms,
        lesson_requirements=problem.lesson_requirements,
        teacher_assignments=teacher_assignments,
        teacher_availability=problem.teacher_availability,
        teacher_free_afternoons=problem.teacher_free_afternoons,
        room_availability=problem.room_availability,
        slots=problem.slots,
    )

    result = solve_problem(problem)

    assert result.is_successful

    for slot in {
        (assignment.day, assignment.period_id)
        for assignment in result.assignments
    }:
        teacher_assignments_at_slot = [
            assignment
            for assignment in result.assignments
            if assignment.teacher_id == teacher_id
            and (assignment.day, assignment.period_id) == slot
        ]

        assert len(teacher_assignments_at_slot) <= 1


def test_teaching_group_clash_is_prevented():
    """A teaching group cannot receive two lessons in one slot."""

    problem = build_constraint_problem(
        teacher_count=2,
        group_count=1,
        room_count=2,
    )

    result = solve_problem(problem)

    assert result.is_successful

    group_id = problem.instructional_groups[0].id

    for slot in {
        (assignment.day, assignment.period_id)
        for assignment in result.assignments
    }:
        group_assignments = [
            assignment
            for assignment in result.assignments
            if assignment.instructional_group_id == group_id
            and (assignment.day, assignment.period_id) == slot
        ]

        assert len(group_assignments) <= 1


def test_room_clash_is_prevented():
    """A room cannot host two lessons in one slot."""

    problem = build_constraint_problem(
        teacher_count=2,
        group_count=2,
        room_count=1,
    )

    result = solve_problem(problem)

    assert result.is_successful

    room_id = problem.rooms[0].id

    for slot in {
        (assignment.day, assignment.period_id)
        for assignment in result.assignments
    }:
        room_assignments = [
            assignment
            for assignment in result.assignments
            if assignment.room_id == room_id
            and (assignment.day, assignment.period_id) == slot
        ]

        assert len(room_assignments) <= 1


def test_teacher_unavailability_is_respected():
    """A teacher cannot be scheduled in a hard unavailable slot."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    teacher_id = problem.teachers[0].id
    monday_period_id = problem.periods[0].id

    availability = (
        TeacherAvailabilityEntity(
            id=uuid4(),
            teacher_id=teacher_id,
            day=DayOfWeek.MONDAY,
            period_id=monday_period_id,
            is_available=False,
        ),
    )

    problem = SchedulingProblem.from_iterables(
        periods=problem.periods,
        teachers=problem.teachers,
        instructional_groups=problem.instructional_groups,
        rooms=problem.rooms,
        lesson_requirements=problem.lesson_requirements,
        teacher_assignments=problem.teacher_assignments,
        teacher_availability=availability,
        teacher_free_afternoons=problem.teacher_free_afternoons,
        room_availability=problem.room_availability,
        slots=problem.slots,
    )

    result = solve_problem(problem)

    assert result.is_successful

    assert all(
        not (
            assignment.teacher_id == teacher_id
            and assignment.day == DayOfWeek.MONDAY
            and assignment.period_id == monday_period_id
        )
        for assignment in result.assignments
    )


def test_room_unavailability_is_respected():
    """A room cannot be used during a hard unavailable slot."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    room_id = problem.rooms[0].id
    monday_period_id = problem.periods[0].id

    room_availability = (
        RoomAvailabilityEntity(
            id=uuid4(),
            room_id=room_id,
            day=DayOfWeek.MONDAY,
            period_id=monday_period_id,
            is_available=False,
        ),
        RoomAvailabilityEntity(
            id=uuid4(),
            room_id=room_id,
            day=DayOfWeek.TUESDAY,
            period_id=problem.periods[1].id,
            is_available=True,
        ),
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
        room_availability=room_availability,
        slots=problem.slots,
    )

    result = solve_problem(problem)

    assert result.is_successful

    assert all(
        not (
            assignment.room_id == room_id
            and assignment.day == DayOfWeek.MONDAY
            and assignment.period_id == monday_period_id
        )
        for assignment in result.assignments
    )


def test_lesson_requirement_is_fulfilled():
    """Every active lesson requirement receives its required periods."""

    problem = build_constraint_problem(
        teacher_count=2,
        group_count=2,
        room_count=2,
        periods_per_week=1,
    )

    result = solve_problem(problem)

    assert result.is_successful

    for requirement in problem.lesson_requirements:
        assignments = [
            assignment
            for assignment in result.assignments
            if assignment.lesson_requirement_id == requirement.id
        ]

        assert len(assignments) == requirement.periods_per_week


def test_lesson_requirement_is_not_repeated_on_one_day():
    """A requirement uses separate days unless double lessons are modelled."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
        periods_per_week=2,
    )

    result = solve_problem(problem)

    assert result.is_successful

    assignments = [
        assignment
        for assignment in result.assignments
        if assignment.lesson_requirement_id == problem.lesson_requirements[0].id
    ]

    assert {assignment.day for assignment in assignments} == {
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
    }


def test_missing_teacher_assignment_is_placed_without_teacher():
    """A requirement with no eligible teacher can still be placed without a teacher."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
        teacher_assignments=(),
    )

    result = solve_problem(problem)

    assert result.status == SolverStatus.OPTIMAL
    assert len(result.assignments) == 1
    assert result.assignments[0].teacher_id is None


def test_teacher_free_afternoon_is_hard_constraint():
    """A teacher cannot teach during their designated free afternoon."""

    teacher_id = uuid4()
    group_id = uuid4()
    room_id = uuid4()
    requirement_id = uuid4()
    period_id = uuid4()

    periods = (
        PeriodEntity(
            id=period_id,
            number=2,
            name="Monday Afternoon Period",
            start_time=time(14, 0),
            end_time=time(14, 40),
            part_of_day=PartOfDay.AFTERNOON,
            is_teaching_period=True,
        ),
    )

    teachers = (
        TeacherEntity(
            id=teacher_id,
            name="Teacher 1",
            code="T001",
        ),
    )

    instructional_groups = (
        InstructionalGroupEntity(
            id=group_id,
            name="Group 1",
            code="G001",
        ),
    )

    rooms = (
        RoomEntity(
            id=room_id,
            name="Room 1",
            code="R001",
            capacity=50,
        ),
    )

    requirements = (
        LessonRequirementEntity(
            id=requirement_id,
            instructional_group_id=group_id,
            subject_id=uuid4(),
            periods_per_week=1,
        ),
    )

    teacher_assignments = (
        TeacherAssignmentEntity(
            id=uuid4(),
            teacher_id=teacher_id,
            lesson_requirement_id=requirement_id,
        ),
    )

    free_afternoons = (
        TeacherFreeAfternoonEntity(
            id=uuid4(),
            teacher_id=teacher_id,
            day=DayOfWeek.MONDAY,
        ),
    )

    slots = (
        TimetableSlot(
            day=DayOfWeek.MONDAY,
            period_id=period_id,
            period_number=2,
            part_of_day=PartOfDay.AFTERNOON,
        ),
    )

    room_availability = (
        RoomAvailabilityEntity(
            id=uuid4(),
            room_id=room_id,
            day=DayOfWeek.MONDAY,
            period_id=period_id,
            is_available=True,
        ),
    )

    problem = SchedulingProblem.from_iterables(
        periods=periods,
        teachers=teachers,
        instructional_groups=instructional_groups,
        rooms=rooms,
        lesson_requirements=requirements,
        teacher_assignments=teacher_assignments,
        teacher_availability=(),
        teacher_free_afternoons=free_afternoons,
        room_availability=room_availability,
        slots=slots,
    )

    result = solve_problem(problem)

    assert result.status == SolverStatus.INFEASIBLE


def test_teacher_free_afternoon_does_not_block_morning():
    """A free afternoon must not prevent morning teaching."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    result = solve_problem(problem)

    assert result.is_successful

    teacher_id = problem.teachers[0].id

    assert any(
        assignment.teacher_id == teacher_id
        for assignment in result.assignments
    )


def test_inactive_teacher_assignment_allows_teacherless_placement():
    """An inactive teacher assignment is ignored and the class may be placed without a teacher."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    assignment = problem.teacher_assignments[0]

    inactive_assignment = TeacherAssignmentEntity(
        id=assignment.id,
        teacher_id=assignment.teacher_id,
        lesson_requirement_id=assignment.lesson_requirement_id,
        is_active=False,
    )

    problem = SchedulingProblem.from_iterables(
        periods=problem.periods,
        teachers=problem.teachers,
        instructional_groups=problem.instructional_groups,
        rooms=problem.rooms,
        lesson_requirements=problem.lesson_requirements,
        teacher_assignments=(inactive_assignment,),
        teacher_availability=problem.teacher_availability,
        teacher_free_afternoons=problem.teacher_free_afternoons,
        room_availability=problem.room_availability,
        slots=problem.slots,
    )

    result = solve_problem(problem)

    assert result.status == SolverStatus.OPTIMAL
    assert len(result.assignments) == 1
    assert result.assignments[0].teacher_id is None


def test_inactive_teacher_cannot_be_scheduled_and_teacherless_placement_is_allowed():
    """An inactive teacher cannot receive the lesson; the class may remain teacherless."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    teacher = problem.teachers[0]

    inactive_teacher = TeacherEntity(
        id=teacher.id,
        name=teacher.name,
        code=teacher.code,
        is_active=False,
    )

    problem = SchedulingProblem.from_iterables(
        periods=problem.periods,
        teachers=(inactive_teacher,),
        instructional_groups=problem.instructional_groups,
        rooms=problem.rooms,
        lesson_requirements=problem.lesson_requirements,
        teacher_assignments=problem.teacher_assignments,
        teacher_availability=problem.teacher_availability,
        teacher_free_afternoons=(),
        room_availability=problem.room_availability,
        slots=problem.slots,
    )

    result = solve_problem(problem)

    assert result.status == SolverStatus.OPTIMAL
    assert len(result.assignments) == 1
    assert result.assignments[0].teacher_id is None


def test_inactive_room_cannot_be_scheduled():
    """An inactive room cannot host a lesson."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    room = problem.rooms[0]

    inactive_room = RoomEntity(
        id=room.id,
        name=room.name,
        code=room.code,
        capacity=room.capacity,
        is_active=False,
    )

    problem = SchedulingProblem.from_iterables(
        periods=problem.periods,
        teachers=problem.teachers,
        instructional_groups=problem.instructional_groups,
        rooms=(inactive_room,),
        lesson_requirements=problem.lesson_requirements,
        teacher_assignments=problem.teacher_assignments,
        teacher_availability=problem.teacher_availability,
        teacher_free_afternoons=problem.teacher_free_afternoons,
        room_availability=problem.room_availability,
        slots=problem.slots,
    )

    result = solve_problem(problem)

    assert result.status == SolverStatus.INFEASIBLE


def test_inactive_lesson_requirement_is_not_scheduled():
    """An inactive lesson requirement must not be scheduled."""

    problem = build_constraint_problem(
        teacher_count=1,
        group_count=1,
        room_count=1,
    )

    requirement = problem.lesson_requirements[0]

    inactive_requirement = LessonRequirementEntity(
        id=requirement.id,
        instructional_group_id=requirement.instructional_group_id,
        subject_id=requirement.subject_id,
        periods_per_week=requirement.periods_per_week,
        is_active=False,
    )

    problem = SchedulingProblem.from_iterables(
        periods=problem.periods,
        teachers=problem.teachers,
        instructional_groups=problem.instructional_groups,
        rooms=problem.rooms,
        lesson_requirements=(inactive_requirement,),
        teacher_assignments=problem.teacher_assignments,
        teacher_availability=problem.teacher_availability,
        teacher_free_afternoons=problem.teacher_free_afternoons,
        room_availability=problem.room_availability,
        slots=problem.slots,
    )

    result = solve_problem(problem)

    assert result.is_successful
    assert result.assignments == ()








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
            number=2,
            name="Tuesday Period 2",
            start_time=time(8, 40),
            end_time=time(9, 20),
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
            period_number=2,
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