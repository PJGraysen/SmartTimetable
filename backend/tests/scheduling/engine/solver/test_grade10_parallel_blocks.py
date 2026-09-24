from datetime import time
from uuid import uuid4

from apps.scheduling.engine.application.grade10_parallel_blocks import (
    GRADE10_PARALLEL_BLOCKS,
    get_grade10_parallel_block_for_subject,
    validate_grade10_parallel_blocks,
)
from apps.scheduling.engine.domain.entities import (
    InstructionalGroupEntity,
    LessonRequirementEntity,
    PeriodEntity,
    RoomEntity,
    TimetableSlot,
)
from apps.scheduling.engine.domain.enums import DayOfWeek, PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver


def test_grade10_parallel_block_configuration_is_authoritative():
    validate_grade10_parallel_blocks()

    assert [
        (
            block.code,
            block.subject_codes,
            block.weekly_shared_slots,
        )
        for block in GRADE10_PARALLEL_BLOCKS
    ] == [
        ("OPTION_1", ("BIO", "MUS", "FRE"), 5),
        ("OPTION_2", ("CHEM", "PHY", "LIT"), 5),
        ("OPTION_3", ("GEO", "HIS", "CS"), 5),
        ("OPTION_4", ("BUS", "AGR"), 5),
    ]
    assert get_grade10_parallel_block_for_subject(
        "bio"
    ) == GRADE10_PARALLEL_BLOCKS[0]
    assert get_grade10_parallel_block_for_subject("ENG") is None


def test_grade10_option_subjects_share_the_same_weekly_slots():
    group = InstructionalGroupEntity(
        id=uuid4(),
        name="Grade 10E",
        code="10E",
    )
    period_id = uuid4()
    period = PeriodEntity(
        id=period_id,
        number=2,
        name="Period 2",
        start_time=time(8, 40),
        end_time=time(9, 20),
        part_of_day=PartOfDay.MORNING,
        is_teaching_period=True,
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
            period_number=period.number,
            part_of_day=period.part_of_day,
        )
        for day in days
    )
    rooms = tuple(
        RoomEntity(
            id=uuid4(),
            name=f"Room {index}",
            code=f"R{index}",
            capacity=50,
        )
        for index in range(1, 4)
    )
    requirements = tuple(
        LessonRequirementEntity(
            id=uuid4(),
            instructional_group_id=group.id,
            subject_id=uuid4(),
            periods_per_week=5,
            requirement_type="BLOCK",
            subject_code=subject_code,
        )
        for subject_code in ("BIO", "MUS", "FRE")
    )
    problem = SchedulingProblem.from_iterables(
        periods=(period,),
        teachers=(),
        instructional_groups=(group,),
        rooms=rooms,
        lesson_requirements=requirements,
        teacher_assignments=(),
        teacher_availability=(),
        teacher_free_afternoons=(),
        room_availability=(),
        slots=slots,
    )

    result = CPSATSolver(
        time_limit_seconds=10.0,
        num_workers=1,
    ).solve(
        problem=problem,
        solver_model=SolverModelBuilder().build(problem),
    )

    assert result.is_successful
    assert len(result.assignments) == 15
    assert all(
        assignment.room_id is not None
        for assignment in result.assignments
    )

    slots_by_requirement = {
        requirement.id: {
            (assignment.day, assignment.period_id)
            for assignment in result.assignments
            if assignment.lesson_requirement_id == requirement.id
        }
        for requirement in requirements
    }

    assert all(
        len(scheduled_slots) == 5
        for scheduled_slots in slots_by_requirement.values()
    )
    assert len(
        {
            frozenset(scheduled_slots)
            for scheduled_slots in slots_by_requirement.values()
        }
    ) == 1
    assert all(
        len(
            {
                assignment.room_id
                for assignment in result.assignments
                if (
                    assignment.day,
                    assignment.period_id,
                ) == slot_key
            }
        ) == 3
        for slot_key in {
            (
                assignment.day,
                assignment.period_id,
            )
            for assignment in result.assignments
        }
    )
