"""STT-032-D regression tests for Senior cross-class synchronization.

The original method reused a leaked loop variable (group_code) after
the per-class representative loop, so each class's contract slots were
resolved using only the second class's group code. When the two classes
expose different contract slots for the same block, the synchronization
silently applied only to the second class's slot set.

The fix resolves each class's contract slots independently and raises
if the two sets differ.
"""
from __future__ import annotations

from datetime import time
from uuid import uuid4

import pytest
from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.entities import (
    InstructionalGroupEntity,
    LessonRequirementEntity,
    PeriodEntity,
)
from apps.scheduling.engine.domain.enums import PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver import model as solver_model

AssignmentVariable = solver_model.AssignmentVariable
SolverModelBuilder = solver_model.SolverModelBuilder


def _periods():
    return tuple(
        PeriodEntity(
            id=uuid4(),
            number=n,
            name=f"Period {n}",
            start_time=time(8, 0),
            end_time=time(8, 40),
            part_of_day=PartOfDay.MORNING,
            is_teaching_period=True,
            is_active=True,
        )
        for n in range(1, 16)
    )


def _build_problem_and_variables():
    periods = _periods()
    period_id_by_number = {p.number: p.id for p in periods}

    groups = (
        InstructionalGroupEntity(
            id=uuid4(), name="Form 3 East", code="3E", is_active=True,
        ),
        InstructionalGroupEntity(
            id=uuid4(), name="Form 3 West", code="3W", is_active=True,
        ),
    )

    requirements = []
    req_by_group_and_block = {}
    for block_code in solver_model.SENIOR_SCHOOL_SYNCHRONIZED_BLOCK_CODES:
        expected = solver_model._senior_school_block_subject_codes(block_code)
        rep = min(expected)
        for g in groups:
            req = LessonRequirementEntity(
                id=uuid4(),
                instructional_group_id=g.id,
                subject_id=uuid4(),
                periods_per_week=5,
                requirement_type="BLOCK",
                subject_code=rep,
                is_active=True,
            )
            requirements.append(req)
            req_by_group_and_block[(g.code, block_code)] = req

    problem = SchedulingProblem.from_iterables(
        periods=periods,
        teachers=(),
        instructional_groups=groups,
        rooms=(),
        lesson_requirements=tuple(requirements),
        teacher_assignments=(),
        teacher_availability=(),
        teacher_free_afternoons=(),
        room_availability=(),
        slots=(),
    )

    model = cp_model.CpModel()
    variables = []
    for block_code in solver_model.SENIOR_SCHOOL_SYNCHRONIZED_BLOCK_CODES:
        for g in groups:
            req = req_by_group_and_block[(g.code, block_code)]
            contract = solver_model._senior_school_block_slots_for_code(
                block_code, group_code=g.code,
            )
            for day, period_number in contract:
                pid = period_id_by_number.get(int(period_number))
                if pid is None:
                    continue
                variables.append(
                    AssignmentVariable(
                        lesson_requirement_id=req.id,
                        teacher_id=None,
                        instructional_group_id=g.id,
                        period_id=pid,
                        day=str(day).strip().upper(),
                        room_id=None,
                        variable=model.new_bool_var(
                            f"v_{g.code}_{block_code}_{day}_{period_number}"
                        ),
                    )
                )

    return problem, model, variables


def test_symmetric_contract_slots_build_without_raise():
    problem, model, variables = _build_problem_and_variables()
    SolverModelBuilder()._add_senior_school_cross_class_synchronization_constraints(
        model=model,
        problem=problem,
        variables=variables,
    )


def test_asymmetric_contract_slots_raise(monkeypatch):
    import apps.scheduling.engine.application.grade10_parallel_blocks as g10

    original = g10.SENIOR_SCHOOL_BLOCK_SLOTS
    asymmetric = {g: dict(b) for g, b in original.items()}

    three_w_sci = list(asymmetric.get("3W", {}).get("SCIENCE", ()))
    if not three_w_sci:
        pytest.skip("No 3W/SCIENCE slots in contract; cannot synthesize asymmetry.")

    asymmetric["3W"]["SCIENCE"] = tuple(three_w_sci[:-1])

    monkeypatch.setattr(g10, "SENIOR_SCHOOL_BLOCK_SLOTS", asymmetric)

    problem, model, variables = _build_problem_and_variables()

    with pytest.raises(ValueError, match="symmetric contract slots"):
        SolverModelBuilder()._add_senior_school_cross_class_synchronization_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )
