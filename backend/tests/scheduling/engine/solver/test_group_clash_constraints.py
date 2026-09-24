"""
STT-032 - group-clash aggregation tests.

The defect under test is in SolverModelBuilder._add_group_clash_constraints:
the pre-fix implementation represented an entire synchronized block using a
single representative requirement. When a non-representative block member
was scheduled and the representative was not, the block presence became
zero and an ordinary requirement could occupy the same physical cell.

Tests 1 and 2 cannot be exercised through CPSATSolver: the Grade 10 and
Senior block co-scheduling constraints force every member of a block into
the same physical slots, so a satisfiable end-to-end problem never presents
the offending configuration. Those scenarios are therefore proven at the
model level by calling _add_group_clash_constraints directly on a raw
cp_model.CpModel.
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
    TimetableSlot,
)
from apps.scheduling.engine.domain.enums import DayOfWeek, PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver import model as solver_model

AssignmentVariable = solver_model.AssignmentVariable
SolverModelBuilder = solver_model.SolverModelBuilder
senior_school_block_code_for_subject = (
    solver_model.senior_school_block_code_for_subject
)


_PERIOD = PeriodEntity(
    id=uuid4(),
    number=2,
    name="Period 2",
    start_time=time(8, 40),
    end_time=time(9, 20),
    part_of_day=PartOfDay.MORNING,
    is_teaching_period=True,
)


def _slot() -> TimetableSlot:
    return TimetableSlot(
        day=DayOfWeek.MONDAY,
        period_id=_PERIOD.id,
        period_number=_PERIOD.number,
        part_of_day=_PERIOD.part_of_day,
    )


def _group(*, code: str) -> InstructionalGroupEntity:
    return InstructionalGroupEntity(
        id=uuid4(),
        name=f"Group {code}",
        code=code,
    )


def _requirement(
    *,
    group: InstructionalGroupEntity,
    subject_code: str,
    requirement_type: str,
    periods_per_week: int = 5,
) -> LessonRequirementEntity:
    return LessonRequirementEntity(
        id=uuid4(),
        instructional_group_id=group.id,
        subject_id=uuid4(),
        periods_per_week=periods_per_week,
        requirement_type=requirement_type,
        subject_code=subject_code,
    )


def _problem(
    *,
    groups: tuple[InstructionalGroupEntity, ...],
    requirements: tuple[LessonRequirementEntity, ...],
) -> SchedulingProblem:
    return SchedulingProblem.from_iterables(
        periods=(_PERIOD,),
        teachers=(),
        instructional_groups=groups,
        rooms=(),
        lesson_requirements=requirements,
        teacher_assignments=(),
        teacher_availability=(),
        teacher_free_afternoons=(),
        room_availability=(),
        slots=(_slot(),),
    )


def _variable(
    *,
    model: cp_model.CpModel,
    group: InstructionalGroupEntity,
    requirement: LessonRequirementEntity,
    name_suffix: str,
) -> AssignmentVariable:
    return AssignmentVariable(
        lesson_requirement_id=requirement.id,
        teacher_id=None,
        instructional_group_id=group.id,
        period_id=_PERIOD.id,
        day=DayOfWeek.MONDAY.value,
        room_id=None,
        variable=model.new_bool_var(f"v_{name_suffix}"),
    )


def _solve(model: cp_model.CpModel) -> int:
    solver = cp_model.CpSolver()
    return solver.solve(model)


_SENIOR_CANDIDATE_CODES = (
    "BIO", "CHEM", "PHY", "HIS", "GEO", "CRE", "IRE",
    "LIT", "FRE", "KIS", "MAT", "ENG", "CS", "BST", "AGR",
)


def _find_senior_subject_code() -> str:
    for code in _SENIOR_CANDIDATE_CODES:
        if senior_school_block_code_for_subject(code) is not None:
            return code
    pytest.skip("No Senior School block subject found in the contract.")


def test_non_representative_block_member_plus_ordinary_is_rejected() -> None:
    group = _group(code="10E")
    bio = _requirement(group=group, subject_code="BIO", requirement_type="BLOCK")
    mus = _requirement(group=group, subject_code="MUS", requirement_type="BLOCK")
    eng = _requirement(group=group, subject_code="ENG", requirement_type="CORE")

    problem = _problem(groups=(group,), requirements=(bio, mus, eng))
    model = cp_model.CpModel()

    bio_var = _variable(model=model, group=group, requirement=bio, name_suffix="bio")
    mus_var = _variable(model=model, group=group, requirement=mus, name_suffix="mus")
    eng_var = _variable(model=model, group=group, requirement=eng, name_suffix="eng")

    SolverModelBuilder()._add_group_clash_constraints(
        model=model,
        problem=problem,
        variables=[bio_var, mus_var, eng_var],
    )

    representative_id = min((bio.id, mus.id), key=str)

    if bio.id == representative_id:
        model.add(bio_var.variable == 0)
        model.add(mus_var.variable == 1)
    else:
        model.add(bio_var.variable == 1)
        model.add(mus_var.variable == 0)

    model.add(eng_var.variable == 1)

    assert _solve(model) == cp_model.INFEASIBLE


def test_two_distinct_blocks_in_same_cell_are_rejected() -> None:
    group = _group(code="10E")
    bio = _requirement(group=group, subject_code="BIO", requirement_type="BLOCK")
    chem = _requirement(group=group, subject_code="CHEM", requirement_type="BLOCK")

    problem = _problem(groups=(group,), requirements=(bio, chem))
    model = cp_model.CpModel()

    bio_var = _variable(model=model, group=group, requirement=bio, name_suffix="bio")
    chem_var = _variable(model=model, group=group, requirement=chem, name_suffix="chem")

    SolverModelBuilder()._add_group_clash_constraints(
        model=model,
        problem=problem,
        variables=[bio_var, chem_var],
    )

    model.add(bio_var.variable == 1)
    model.add(chem_var.variable == 1)

    assert _solve(model) == cp_model.INFEASIBLE


def test_multiple_members_of_same_block_in_one_cell_are_allowed() -> None:
    group = _group(code="10E")
    bio = _requirement(group=group, subject_code="BIO", requirement_type="BLOCK")
    mus = _requirement(group=group, subject_code="MUS", requirement_type="BLOCK")
    fre = _requirement(group=group, subject_code="FRE", requirement_type="BLOCK")

    problem = _problem(groups=(group,), requirements=(bio, mus, fre))
    model = cp_model.CpModel()

    variables = [
        _variable(model=model, group=group, requirement=r, name_suffix=r.subject_code.lower())
        for r in (bio, mus, fre)
    ]

    SolverModelBuilder()._add_group_clash_constraints(
        model=model,
        problem=problem,
        variables=variables,
    )

    for v in variables:
        model.add(v.variable == 1)

    assert _solve(model) in {cp_model.FEASIBLE, cp_model.OPTIMAL}


def test_grade10_and_senior_block_namespaces_remain_distinct() -> None:
    senior_subject_code = _find_senior_subject_code()

    g10_group = _group(code="10E")
    g10_req = _requirement(group=g10_group, subject_code="BIO", requirement_type="BLOCK")

    senior_group = _group(code="3E")
    senior_req = _requirement(
        group=senior_group,
        subject_code=senior_subject_code,
        requirement_type="BLOCK",
    )

    problem = _problem(
        groups=(g10_group, senior_group),
        requirements=(g10_req, senior_req),
    )
    model = cp_model.CpModel()

    g10_var = _variable(model=model, group=g10_group, requirement=g10_req, name_suffix="g10")
    senior_var = _variable(model=model, group=senior_group, requirement=senior_req, name_suffix="senior")

    SolverModelBuilder()._add_group_clash_constraints(
        model=model,
        problem=problem,
        variables=[g10_var, senior_var],
    )

    names = {v.name for v in model.Proto().variables}

    g10_block_names = {
        n for n in names
        if n.startswith("parallel_block_presence_") and "_GRADE10_" in n
    }
    senior_block_names = {
        n for n in names
        if n.startswith("parallel_block_presence_") and "_SENIOR_" in n
    }

    assert g10_block_names, "Expected a Grade 10 block presence variable."
    assert senior_block_names, "Expected a Senior block presence variable."
    assert g10_block_names.isdisjoint(senior_block_names)


@pytest.mark.parametrize(
    "group_code, block_subject_code",
    [
        ("10E", "BIO"),
        ("3E", None),
    ],
)
def test_ordinary_requirement_is_mutually_exclusive_with_any_block(
    group_code: str,
    block_subject_code: str | None,
) -> None:
    if block_subject_code is None:
        block_subject_code = _find_senior_subject_code()

    group = _group(code=group_code)
    block_req = _requirement(
        group=group,
        subject_code=block_subject_code,
        requirement_type="BLOCK",
    )
    ordinary = _requirement(
        group=group,
        subject_code="ENG",
        requirement_type="CORE",
    )

    problem = _problem(groups=(group,), requirements=(block_req, ordinary))
    model = cp_model.CpModel()

    block_var = _variable(model=model, group=group, requirement=block_req, name_suffix="blk")
    ordinary_var = _variable(model=model, group=group, requirement=ordinary, name_suffix="ord")

    SolverModelBuilder()._add_group_clash_constraints(
        model=model,
        problem=problem,
        variables=[block_var, ordinary_var],
    )

    model.add(block_var.variable == 1)
    model.add(ordinary_var.variable == 1)

    assert _solve(model) == cp_model.INFEASIBLE
