"""
RC#2 - Form 4 TECHNICALS_APPLIED FRI-9 -> THU-10.

Before the fix, FORM4_TECHNICALS_APPLIED_SLOTS contained ('FRI', 9).
FORM4_HUMANITIES_SLOTS also contained ('FRI', 9). Both blocks have
exactly 4 candidates for a 4-period quota, so both were forced into
FRI-9, making the physical-cell constraint unsatisfiable.

The fix replaces the Form-4 TECH entry with ('THU', 10), the 8th
teaching slot on Thursday (matching the 8th teaching slot position that
FRI-9 occupied on Friday, since raw periods 5 and 9 are non-teaching).

Test 4 uses a synthetic in-memory SchedulingProblem (no DB) that
mirrors the production period layout (raw 1..12 with raw 5 and 9 as
non-teaching Break/Lunch). It exercises the actual constants through
the same _contract_slot_keys path the production model uses.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import time
from uuid import uuid4

from apps.scheduling.engine.application import grade10_parallel_blocks as g10
from apps.scheduling.engine.domain.entities import PeriodEntity
from apps.scheduling.engine.domain.enums import PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver import model as m


def test_form4_tech_no_longer_contains_fri_9():
    slots = g10.FORM4_TECHNICALS_APPLIED_SLOTS
    assert ("FRI", 9) not in slots, (
        "FORM4_TECHNICALS_APPLIED_SLOTS still contains ('FRI', 9); "
        "the RC#2 fix did not apply."
    )


def test_form4_tech_now_contains_thu_10():
    slots = g10.FORM4_TECHNICALS_APPLIED_SLOTS
    assert ("THU", 10) in slots, (
        "FORM4_TECHNICALS_APPLIED_SLOTS does not contain ('THU', 10); "
        "the RC#2 fix did not apply."
    )


def test_form4_tech_shape_preserved():
    slots = g10.FORM4_TECHNICALS_APPLIED_SLOTS
    assert len(slots) == 4, (
        f"FORM4_TECHNICALS_APPLIED_SLOTS has {len(slots)} entries; "
        "4-for-4 rigidity must be preserved."
    )


def _synthetic_problem() -> SchedulingProblem:
    periods = tuple(
        PeriodEntity(
            id=uuid4(),
            number=n,
            name=f"P{n}",
            start_time=time(8, 0),
            end_time=time(8, 40),
            part_of_day=PartOfDay.MORNING,
            is_teaching_period=(n not in {5, 9}),
            is_active=True,
        )
        for n in range(1, 13)
    )
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


def test_no_cross_rigid_block_collision_in_4e_4w():
    """
    After the fix, no two saturated (candidates == quota) senior rigid
    blocks in 4E or 4W should share a physical cell.
    """
    problem = _synthetic_problem()

    for stream in ("4E", "4W"):
        cells_by = {}
        quotas = {}
        for block_code in m.SENIOR_SCHOOL_SYNCHRONIZED_BLOCK_CODES:
            raw = m._senior_school_block_slots_for_code(
                block_code, group_code=stream
            )
            resolved = m._contract_slot_keys(raw, problem)
            cells_by[block_code] = resolved
            quotas[block_code] = m._senior_school_block_weekly_shared_slots(
                block_code
            )

        saturated = {
            bc for bc, cells in cells_by.items()
            if len(cells) == quotas[bc]
        }

        owners = defaultdict(list)
        for bc in saturated:
            for cell in cells_by[bc]:
                owners[cell].append(bc)

        collisions = {
            cell: blocks for cell, blocks in owners.items()
            if len(blocks) > 1
        }

        assert not collisions, (
            f"{stream} has saturated-block collisions after RC#2 fix: "
            f"{collisions}"
        )
