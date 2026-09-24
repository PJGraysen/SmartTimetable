"""RC#3 B2 - synchronized teacher-event collapse tests."""
from __future__ import annotations

from datetime import time
from types import SimpleNamespace
from uuid import uuid4

from ortools.sat.python import cp_model

from apps.scheduling.engine.domain.entities import (
    InstructionalGroupEntity,
    LessonRequirementEntity,
    PeriodEntity,
    TimetableSlot,
)
from apps.scheduling.engine.domain.enums import DayOfWeek, PartOfDay
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver import model as m


AssignmentVariable = m.AssignmentVariable
SolverModelBuilder = m.SolverModelBuilder


_PERIOD = PeriodEntity(
    id=uuid4(), number=2, name="P2",
    start_time=time(8, 40), end_time=time(9, 20),
    part_of_day=PartOfDay.MORNING, is_teaching_period=True, is_active=True,
)


def _group(code: str) -> InstructionalGroupEntity:
    return InstructionalGroupEntity(id=uuid4(), name=code, code=code)


def _req(group, subject_code, requirement_type="BLOCK", ppw=5):
    return LessonRequirementEntity(
        id=uuid4(),
        instructional_group_id=group.id,
        subject_id=uuid4(),
        periods_per_week=ppw,
        requirement_type=requirement_type,
        subject_code=subject_code,
    )


def _teacher(tid):
    return SimpleNamespace(id=tid, is_active=True)


def _free_afternoon(tid):
    # Every active teacher must have exactly one active free-afternoon
    # assignment, per SchedulingProblem._validate_teacher_free_afternoons.
    return SimpleNamespace(
        id=uuid4(),
        teacher_id=tid,
        day=DayOfWeek.MONDAY.value,
        is_active=True,
    )


def _ta(req, tid):
    return SimpleNamespace(
        id=uuid4(),
        lesson_requirement_id=req.id,
        teacher_id=tid,
        is_active=True,
    )


def _problem(groups, reqs, tas):
    teacher_ids = sorted({ta.teacher_id for ta in tas}, key=str)
    teachers = tuple(_teacher(tid) for tid in teacher_ids)
    free_afternoons = tuple(_free_afternoon(tid) for tid in teacher_ids)
    return SchedulingProblem.from_iterables(
        periods=(_PERIOD,),
        teachers=teachers,
        instructional_groups=tuple(groups),
        rooms=(),
        lesson_requirements=tuple(reqs),
        teacher_assignments=tuple(tas),
        teacher_availability=(),
        teacher_free_afternoons=free_afternoons,
        room_availability=(),
        slots=(TimetableSlot(
            day=DayOfWeek.MONDAY, period_id=_PERIOD.id,
            period_number=_PERIOD.number, part_of_day=_PERIOD.part_of_day,
        ),),
    )


def _av(model, group, req, teacher_id, tag=""):
    return AssignmentVariable(
        lesson_requirement_id=req.id,
        teacher_id=teacher_id,
        instructional_group_id=group.id,
        period_id=_PERIOD.id,
        day=DayOfWeek.MONDAY.value,
        room_id=None,
        variable=model.new_bool_var(f"v_{tag}_{req.subject_code}"),
    )


def _groups(problem, variables):
    return SolverModelBuilder._synchronized_teacher_event_groups(
        problem=problem, variables=variables,
    )


def test_single_synchronized_pair_is_grouped():
    g_e = _group("10E"); g_w = _group("10W")
    req_e = _req(g_e, "CHEM"); req_w = _req(g_w, "CHEM")
    t = uuid4()
    problem = _problem([g_e, g_w], [req_e, req_w], [_ta(req_e, t), _ta(req_w, t)])
    model = cp_model.CpModel()
    v_e = _av(model, g_e, req_e, t, "e")
    v_w = _av(model, g_w, req_w, t, "w")
    groups = _groups(problem, [v_e, v_w])
    assert len(groups) == 1
    assert len(next(iter(groups.values()))) == 2


def test_distinct_subjects_same_teacher_not_grouped():
    g_e = _group("10E"); g_w = _group("10W")
    r1 = _req(g_e, "CHEM"); r2 = _req(g_w, "PHY")
    t = uuid4()
    problem = _problem([g_e, g_w], [r1, r2], [_ta(r1, t), _ta(r2, t)])
    model = cp_model.CpModel()
    v1 = _av(model, g_e, r1, t, "e1")
    v2 = _av(model, g_w, r2, t, "w2")
    assert _groups(problem, [v1, v2]) == {}


def test_different_teachers_same_subject_not_grouped():
    g_e = _group("10E"); g_w = _group("10W")
    r_e = _req(g_e, "CHEM"); r_w = _req(g_w, "CHEM")
    t1, t2 = uuid4(), uuid4()
    problem = _problem([g_e, g_w], [r_e, r_w], [_ta(r_e, t1), _ta(r_w, t2)])
    model = cp_model.CpModel()
    v1 = _av(model, g_e, r_e, t1, "e")
    v2 = _av(model, g_w, r_w, t2, "w")
    assert _groups(problem, [v1, v2]) == {}


def test_non_paired_groups_not_collapsed():
    g10 = _group("10E"); g9 = _group("9E")
    r1 = _req(g10, "CHEM"); r2 = _req(g9, "CHEM")
    t = uuid4()
    problem = _problem([g10, g9], [r1, r2], [_ta(r1, t), _ta(r2, t)])
    model = cp_model.CpModel()
    v1 = _av(model, g10, r1, t, "10e")
    v2 = _av(model, g9, r2, t, "9e")
    assert _groups(problem, [v1, v2]) == {}


EXPECTED_PAIRS = {
    ("OPTION_1", "BIO"), ("OPTION_1", "MUS"),
    ("OPTION_2", "CHEM"), ("OPTION_2", "LIT"), ("OPTION_2", "PHY"),
    ("OPTION_3", "CS"), ("OPTION_3", "GEO"), ("OPTION_3", "HIS"),
    ("OPTION_4", "AGR"), ("OPTION_4", "BUS"),
}


def test_helper_returns_exactly_the_ten_production_pairs():
    g_e = _group("10E"); g_w = _group("10W")
    reqs, tas = [], []
    for _bc, subj in sorted(EXPECTED_PAIRS):
        t_subj = uuid4()
        r_e = _req(g_e, subj); r_w = _req(g_w, subj)
        reqs += [r_e, r_w]
        tas += [_ta(r_e, t_subj), _ta(r_w, t_subj)]
    problem = _problem([g_e, g_w], reqs, tas)
    model = cp_model.CpModel()
    vars_ = []
    for i, r in enumerate(reqs):
        t = tas[i].teacher_id
        grp = g_e if r.instructional_group_id == g_e.id else g_w
        vars_.append(_av(model, grp, r, t, f"{r.subject_code}_{i}"))
    groups = _groups(problem, vars_)
    actual = {(k[0], k[1]) for k in groups.keys()}
    assert actual == EXPECTED_PAIRS, f"got {sorted(actual)}"


def test_teacher_clash_permits_synchronized_pair_co_occupancy():
    g_e = _group("10E"); g_w = _group("10W")
    r_e = _req(g_e, "CHEM"); r_w = _req(g_w, "CHEM")
    t = uuid4()
    problem = _problem([g_e, g_w], [r_e, r_w], [_ta(r_e, t), _ta(r_w, t)])
    model = cp_model.CpModel()
    v_e = _av(model, g_e, r_e, t, "e")
    v_w = _av(model, g_w, r_w, t, "w")
    SolverModelBuilder()._add_teacher_clash_constraints(
        model=model, problem=problem, variables=[v_e, v_w],
    )
    model.add(v_e.variable == 1)
    model.add(v_w.variable == 1)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert status in (cp_model.FEASIBLE, cp_model.OPTIMAL)
