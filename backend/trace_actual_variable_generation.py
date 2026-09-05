from __future__ import annotations

from collections import Counter, defaultdict

import django

django.setup()

from apps.academics.models import LessonRequirement
from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.models import SchedulingRun


print("=" * 90)
print("SMARTTIMETABLE PRO - ACTUAL CP-SAT VARIABLE GENERATION TRACE")
print("=" * 90)
print()
print("READ-ONLY DIAGNOSTIC")
print("The model builder is invoked only to CREATE CP-SAT variables.")
print("CP-SAT solve() is NOT called.")
print("No timetable is generated.")
print("No database records are changed.")
print()

# ---------------------------------------------------------------------------
# 1. SELECT THE AUTHORITATIVE TERM
# ---------------------------------------------------------------------------
latest_run = (
    SchedulingRun.objects
    .select_related("term")
    .order_by("-created_at", "-id")
    .first()
)

if latest_run is None:
    raise RuntimeError("No SchedulingRun exists; cannot identify the active term.")

term = latest_run.term

print("1. AUTHORITATIVE TERM")
print("-" * 90)
print(f"TERM ID:   {term.id}")
print(f"TERM NAME: {getattr(term, 'name', term)}")
print(f"REFERENCE RUN: {latest_run.id}")
print(f"REFERENCE RUN CREATED: {latest_run.created_at}")
print()

# ---------------------------------------------------------------------------
# 2. DATABASE REQUIREMENTS — SAME TERM USED BY THE REAL LOADER
# ---------------------------------------------------------------------------
db_requirements = list(
    LessonRequirement.objects
    .filter(term=term, is_active=True)
    .select_related("subject", "instructional_group")
    .order_by("instructional_group_id", "subject_id", "id")
)

print("2. ACTIVE DATABASE REQUIREMENTS FOR THAT TERM")
print("-" * 90)
print(f"COUNT: {len(db_requirements)}")
print()

for req in db_requirements:
    subject = getattr(req, "subject", None)
    group = getattr(req, "instructional_group", None)
    code = str(getattr(subject, "code", "") or "").strip().upper()
    group_name = str(getattr(group, "name", "") or group or "")
    print(
        f"{code or '<NO CODE>':8} "
        f"REQ={req.id} "
        f"GROUP={req.instructional_group_id} "
        f"({group_name}) "
        f"WEEK={req.lessons_per_week}"
    )

print()

# ---------------------------------------------------------------------------
# 3. LOAD THE EXACT DOMAIN PROBLEM USED BY SCHEDULING
# ---------------------------------------------------------------------------
loader = DjangoSchedulingLoader()
problem = loader.load_problem(term=term)

print("3. LOADED DOMAIN PROBLEM")
print("-" * 90)
print(f"LESSON REQUIREMENTS: {len(problem.lesson_requirements)}")
print(f"TEACHERS:            {len(problem.teachers)}")
print(f"TEACHING GROUPS:     {len(problem.teaching_groups)}")
print(f"ROOMS:               {len(problem.rooms)}")
print(f"PERIODS:             {len(problem.periods)}")
print(f"SLOTS:               {len(problem.slots)}")
print(f"TEACHER ASSIGNMENTS: {len(problem.teacher_assignments)}")
print()

# ---------------------------------------------------------------------------
# 4. REPRODUCE THE VARIABLE-GENERATION FILTERS EXACTLY
# ---------------------------------------------------------------------------
active_requirements = [
    r for r in problem.lesson_requirements
    if r.is_active
]

active_teachers = [
    t for t in problem.teachers
    if t.is_active
]

active_groups = [
    g for g in problem.teaching_groups
    if g.is_active
]

active_rooms = [
    r for r in problem.rooms
    if r.is_active
]

teachers_by_requirement = defaultdict(list)

for assignment in problem.teacher_assignments:
    if not assignment.is_active:
        continue
    teachers_by_requirement[
        assignment.lesson_requirement_id
    ].append(assignment.teacher_id)

valid_group_ids = {g.id for g in active_groups}
valid_teacher_ids = {t.id for t in active_teachers}
valid_room_ids = {r.id for r in active_rooms}

teaching_slots = []

for slot in problem.slots:
    period = problem.period_by_id.get(slot.period_id)

    if period is None:
        continue

    if not period.is_active:
        continue

    if not period.is_teaching_period:
        continue

    teaching_slots.append(slot)

print("4. VARIABLE-GENERATION INPUTS")
print("-" * 90)
print(f"ACTIVE REQUIREMENTS: {len(active_requirements)}")
print(f"ACTIVE TEACHERS:     {len(active_teachers)}")
print(f"ACTIVE GROUPS:       {len(active_groups)}")
print(f"ACTIVE ROOMS:        {len(active_rooms)}")
print(f"TEACHING SLOTS:      {len(teaching_slots)}")
print()

# ---------------------------------------------------------------------------
# 5. EXACT PRE-CONSTRUCTOR AUDIT
# ---------------------------------------------------------------------------
print("5. REQUIREMENT → TEACHER → SLOT → ROOM ELIGIBILITY")
print("-" * 90)

eligible_summary = []

for requirement in active_requirements:
    subject_code = str(
        getattr(requirement, "subject_code", "") or ""
    ).strip().upper()

    eligible_teacher_ids = [
        teacher_id
        for teacher_id in teachers_by_requirement[requirement.id]
        if teacher_id in valid_teacher_ids
    ]

    valid_group = requirement.teaching_group_id in valid_group_ids

    theoretical_variables = (
        len(eligible_teacher_ids)
        * len(teaching_slots)
        * len(active_rooms)
        if valid_group
        else 0
    )

    row = {
        "id": requirement.id,
        "subject": subject_code or "<NO CODE>",
        "group": requirement.instructional_group_id,
        "weekly": requirement.periods_per_week,
        "teachers": len(eligible_teacher_ids),
        "slots": len(teaching_slots),
        "rooms": len(active_rooms),
        "valid_group": valid_group,
        "theoretical_variables": theoretical_variables,
    }
    eligible_summary.append(row)

    print(
        f"{row['subject']:8} "
        f"GROUP={row['group']} "
        f"WEEK={row['weekly']} "
        f"TEACHERS={row['teachers']} "
        f"SLOTS={row['slots']} "
        f"ROOMS={row['rooms']} "
        f"GROUP_OK={row['valid_group']} "
        f"THEORETICAL_VARS={row['theoretical_variables']}"
    )

print()

# ---------------------------------------------------------------------------
# 6. INVOKE THE ACTUAL VARIABLE GENERATOR
# ---------------------------------------------------------------------------
print("6. ACTUAL SOLVER VARIABLE GENERATION")
print("-" * 90)
print("Calling SolverModelBuilder._create_assignment_variables(...).")
print("This is the actual CP-SAT variable-construction path.")
print()

builder = SolverModelBuilder()

# We need a fresh CP model, but importing cp_model here avoids changing
# the application code.
from ortools.sat.python import cp_model

cp_model_instance = cp_model.CpModel()

variables = builder._create_assignment_variables(
    model=cp_model_instance,
    problem=problem,
)

print(f"ACTUAL AssignmentVariable COUNT: {len(variables)}")
print()

# ---------------------------------------------------------------------------
# 7. ACTUAL VARIABLES BY REQUIREMENT
# ---------------------------------------------------------------------------
actual_by_requirement = defaultdict(list)

for variable in variables:
    actual_by_requirement[
        variable.lesson_requirement_id
    ].append(variable)

print("7. ACTUAL VARIABLES BY REQUIREMENT")
print("-" * 90)

total_expected_weekly = 0
total_actual_variables = 0
missing_generation = []

for requirement in sorted(
    active_requirements,
    key=lambda r: (
        str(getattr(r, "subject_code", "")),
        str(r.instructional_group_id),
        str(r.id),
    ),
):
    subject_code = str(
        getattr(requirement, "subject_code", "") or ""
    ).strip().upper()

    actual = actual_by_requirement.get(requirement.id, [])
    actual_count = len(actual)

    total_expected_weekly += requirement.periods_per_week
    total_actual_variables += actual_count

    if actual_count == 0:
        missing_generation.append(requirement)

    teacher_ids = sorted(
        {str(v.teacher_id) for v in actual}
    )
    period_ids = sorted(
        {str(v.period_id) for v in actual}
    )
    room_ids = sorted(
        {str(v.room_id) for v in actual}
    )
    days = sorted(
        {str(v.day) for v in actual}
    )

    print(
        f"{subject_code:8} "
        f"REQ={requirement.id} "
        f"WEEK={requirement.periods_per_week} "
        f"VARS={actual_count} "
        f"TEACHERS={len(teacher_ids)} "
        f"DAYS={len(days)} "
        f"PERIODS={len(period_ids)} "
        f"ROOMS={len(room_ids)}"
    )

print()

# ---------------------------------------------------------------------------
# 8. HARD INTEGRITY CHECKS
# ---------------------------------------------------------------------------
print("8. VARIABLE-GENERATION INTEGRITY")
print("-" * 90)

print(f"ACTIVE REQUIREMENTS:              {len(active_requirements)}")
print(f"REQUIREMENT WEEKLY TOTAL:         {total_expected_weekly}")
print(f"GENERATED ASSIGNMENT VARIABLES:   {total_actual_variables}")
print(f"REQUIREMENTS WITH ZERO VARIABLES: {len(missing_generation)}")
print()

if missing_generation:
    print("FAIL: REQUIREMENTS WITH NO GENERATED VARIABLES")
    for requirement in missing_generation:
        print(
            f"  REQ={requirement.id} "
            f"SUBJECT={getattr(requirement, 'subject_code', '')} "
            f"GROUP={requirement.instructional_group_id} "
            f"WEEK={requirement.periods_per_week} "
            f"TEACHER_ASSIGNMENTS="
            f"{len(teachers_by_requirement[requirement.id])}"
        )
else:
    print("PASS: EVERY ACTIVE REQUIREMENT HAS AT LEAST ONE VARIABLE")

print()

# ---------------------------------------------------------------------------
# 9. MODEL CONSTRAINT TARGETS — WITHOUT SOLVING
# ---------------------------------------------------------------------------
print("9. LESSON-REQUIREMENT CONSTRAINT TARGETS")
print("-" * 90)

for requirement in sorted(
    active_requirements,
    key=lambda r: (
        str(getattr(r, "subject_code", "")),
        str(r.instructional_group_id),
        str(r.id),
    ),
):
    generated = actual_by_requirement.get(requirement.id, [])
    print(
        f"REQ={requirement.id} "
        f"SUBJECT={getattr(requirement, 'subject_code', '')} "
        f"GROUP={requirement.instructional_group_id} "
        f"TARGET={requirement.periods_per_week} "
        f"VARIABLES={len(generated)}"
    )

print()

# ---------------------------------------------------------------------------
# 10. GROUP/SUBJECT WEEKLY TOTALS
# ---------------------------------------------------------------------------
print("10. WEEKLY CONTRACT TOTALS REPRESENTED IN DOMAIN")
print("-" * 90)

by_group = defaultdict(int)
by_subject = defaultdict(int)

for requirement in active_requirements:
    by_group[requirement.instructional_group_id] += requirement.periods_per_week
    by_subject[
        str(getattr(requirement, "subject_code", "") or "").strip().upper()
    ] += requirement.periods_per_week

for group_id, total in sorted(by_group.items(), key=lambda item: str(item[0])):
    print(f"GROUP {group_id}: WEEKLY REQUIREMENT TOTAL = {total}")

print()
for subject, total in sorted(by_subject.items()):
    print(f"{subject or '<NO CODE>'}: DOMAIN WEEKLY TOTAL = {total}")

print()

# ---------------------------------------------------------------------------
# 11. AUTHORITATIVE CONCLUSION
# ---------------------------------------------------------------------------
print("11. CONCLUSION")
print("-" * 90)

if (
    len(active_requirements) == len(db_requirements)
    and not missing_generation
):
    print("PASS: DATABASE → DOMAIN → VARIABLE-GENERATION REQUIREMENT COVERAGE IS COMPLETE.")
else:
    print("FAIL: REQUIREMENT LOSS EXISTS BEFORE OR DURING VARIABLE GENERATION.")

print()
print("IMPORTANT:")
print("- This trace DOES invoke the real variable-generation function.")
print("- It DOES create in-memory CP-SAT variables.")
print("- It does NOT call CpSolver.solve().")
print("- It does NOT persist a timetable.")
print("- It does NOT modify database records.")
print("- It does NOT modify solver source code.")
print("- It does NOT modify frontend code.")

print()
print("=" * 90)
print("ACTUAL VARIABLE GENERATION TRACE COMPLETE")
print("=" * 90)