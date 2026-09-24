"""
RC#1 - _contract_slot_keys ordinal regression tests.

The business contract stores teaching-period ORDINALS (1 = first
active teaching period, 2 = second, ...). The pre-fix helper treated
the stored period_number as the raw PeriodEntity.number. Whenever a
term contains non-teaching periods (Break, Lunch) between teaching
periods, those two interpretations diverge from the first gap
onwards, and contract slots silently resolve to zero physical slots.

These tests prove the helper maps ordinals correctly, and that it
does not silently drop contract slots that fall past a non-teaching
period.
"""
from __future__ import annotations

from datetime import time
from uuid import uuid4

from apps.scheduling.engine.domain.entities import PeriodEntity
from apps.scheduling.engine.domain.enums import PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.model import _contract_slot_keys


def _period(number: int, *, teaching: bool) -> PeriodEntity:
    return PeriodEntity(
        id=uuid4(),
        number=number,
        name=f"Period {number}",
        start_time=time(8, 0),
        end_time=time(8, 40),
        part_of_day=PartOfDay.MORNING,
        is_teaching_period=teaching,
        is_active=True,
    )


def _problem(periods: tuple[PeriodEntity, ...]) -> SchedulingProblem:
    return SchedulingProblem.from_iterables(
        periods=periods,
        teachers=(),
        instructional_groups=(),
        rooms=(),
        lesson_requirements=(),
        teacher_assignments=(),
        teacher_availability=(),
        teacher_free_afternoons=(),
        room_availability=(),
        slots=(),
    )


def test_contract_slot_keys_maps_period_ordinal_to_teaching_period():
    # Raw layout 1..12, with raw 5 = Break, raw 9 = Lunch.
    periods = tuple(
        _period(n, teaching=(n not in {5, 9}))
        for n in range(1, 13)
    )
    problem = _problem(periods)
    period_id_by_number = {p.number: p.id for p in periods}

    result = _contract_slot_keys(
        (("MON", 1), ("MON", 5), ("MON", 9)),
        problem,
    )

    expected = frozenset({
        ("MON", period_id_by_number[1]),   # ordinal 1 -> raw 1
        ("MON", period_id_by_number[6]),   # ordinal 5 -> raw 6 (skips Break)
        ("MON", period_id_by_number[11]),  # ordinal 9 -> raw 11 (skips Lunch)
    })

    assert result == expected


def test_contract_slot_keys_ignores_non_numeric_ordinals():
    periods = tuple(_period(n, teaching=True) for n in range(1, 5))
    problem = _problem(periods)

    result = _contract_slot_keys(
        (("MON", "not-a-number"), ("MON", None), ("MON", 2)),
        problem,
    )

    assert len(result) == 1
    day, _pid = next(iter(result))
    assert day == "MON"


def test_contract_slot_keys_returns_empty_for_out_of_range_ordinal():
    periods = tuple(_period(n, teaching=True) for n in range(1, 5))
    problem = _problem(periods)

    result = _contract_slot_keys((("MON", 10),), problem)

    assert result == frozenset()
