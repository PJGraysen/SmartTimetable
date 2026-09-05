from __future__ import annotations

from collections import defaultdict
import inspect
import django

django.setup()

from ortools.sat.python import cp_model
from apps.academics.models import LessonRequirement
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.models import SchedulingRun


def safe_len(value):
    try:
        return len(value)
    except Exception:
        return "?"


def public_attrs(obj):
    try:
        return sorted(
            name for name in dir(obj)
            if not name.startswith("_")
        )
    except Exception:
        return []


def describe_collection(name, value):
    print(f"{name}: type={type(value).__name__} count={safe_len(value)}")
    try:
        sample = list(value)[:3]
        for item in sample:
            print(f"    item type={type(item).__name__} value={item!r}")
    except Exception as exc:
        print(f"    sample unavailable: {exc}")


print("=" * 100)
print("SMARTTIMETABLE PRO - ACTUAL CP-SAT VARIABLE GENERATION TRACE v2")
print("=" * 100)
print()
print("READ-ONLY DIAGNOSTIC")
print("The REAL SolverModelBuilder._create_assignment_variables() is invoked.")
print("CpSolver.solve() is NOT called.")
print("No timetable is generated.")
print("No database records are changed.")
print()

# ---------------------------------------------------------------------------
# 1. AUTHORITATIVE TERM
# ---------------------------------------------------------------------------
latest_run = (
    SchedulingRun.objects
    .select_related("term")
    .order_by("-created_at", "-id")
    .first()
)

if latest_run is None:
    raise RuntimeError("No SchedulingRun exists.")

term = latest_run.term

print("1. AUTHORITATIVE TERM")
print("-" * 100)
print(f"TERM ID:       {term.id}")
print(f"TERM NAME:     {getattr(term, 'name', term)}")
print(f"REFERENCE RUN: {latest_run.id}")
print(f"CREATED:       {latest_run.created_at}")
print()

# ---------------------------------------------------------------------------
# 2. DATABASE REQUIREMENTS
# ---------------------------------------------------------------------------
db_requirements = list(
    LessonRequirement.objects
    .filter(term=term, is_active=True)
    .select_related("subject", "instructional_group")
    .order_by("instructional_group_id", "subject_id", "id")
)

print("2. ACTIVE DATABASE REQUIREMENTS")
print("-" * 100)
print(f"COUNT: {len(db_requirements)}")

for req in db_requirements:
    subject = getattr(req, "subject", None)
    group = getattr(req, "instructional_group", None)
    code = str(getattr(subject, "code", "") or "").strip().upper()
    group_name = str(getattr(group, "name", "") or group or "")
    weekly = getattr(req, "periods_per_week",
             getattr(req, "lessons_per_week", "?"))
    print(
        f"{code or '<NO CODE>':8} "
        f"REQ={req.id} "
        f"GROUP={req.instructional_group_id} "
        f"({group_name}) "
        f"WEEK={weekly}"
    )

print()

# ---------------------------------------------------------------------------
# 3. LOAD EXACT DOMAIN PROBLEM
# ---------------------------------------------------------------------------
loader = DjangoSchedulingLoader()
problem = loader.load_problem(term=term)

print("3. LOADED DOMAIN PROBLEM — ACTUAL OBJECT SHAPE")
print("-" * 100)
print(f"TYPE: {type(problem).__module__}.{type(problem).__name__}")
print("PUBLIC ATTRIBUTES:")
print(", ".join(public_attrs(problem)))
print()

# Do NOT assume a field called teaching_groups.
# Print the actual collections present on SchedulingProblem.
candidate_names = [
    "lesson_requirements",
    "teachers",
    "teacher_assignments",
    "rooms",
    "teaching_periods",
    "periods",
    "slots",
    "teaching_slots",
    "groups",
    "teaching_groups",
    "instructional_groups",
    "period_by_id",
    "room_by_id",
    "teacher_by_id",
]

for name in candidate_names:
    if hasattr(problem, name):
        describe_collection(name, getattr(problem, name))

print()

# ---------------------------------------------------------------------------
# 4. INSPECT THE REAL VARIABLE GENERATOR BEFORE INVOKING IT
# ---------------------------------------------------------------------------
builder = SolverModelBuilder()
generator = builder._create_assignment_variables

print("4. REAL VARIABLE GENERATOR")
print("-" * 100)
print(f"CALLABLE: {generator}")
print("SIGNATURE:")
print(inspect.signature(generator))
print()
print("SOURCE:")
try:
    print(inspect.getsource(generator))
except Exception as exc:
    print(f"SOURCE UNAVAILABLE: {exc}")
print()

# ---------------------------------------------------------------------------
# 5. ACTUAL VARIABLE GENERATION — THIS IS THE CRITICAL TEST
# ---------------------------------------------------------------------------
print("5. INVOKING ACTUAL VARIABLE GENERATION")
print("-" * 100)
print("Creating a fresh in-memory CpModel and calling:")
print("SolverModelBuilder._create_assignment_variables(model, problem)")
print()

cp_model_instance = cp_model.CpModel()

try:
    variables = generator(
        model=cp_model_instance,
        problem=problem,
    )
except TypeError:
    # Some implementations may use positional parameters.
    variables = generator(cp_model_instance, problem)

print(f"ACTUAL AssignmentVariable COUNT: {len(variables)}")
print()

# ---------------------------------------------------------------------------
# 6. VARIABLE OBJECT SHAPE
# ---------------------------------------------------------------------------
print("6. ACTUAL ASSIGNMENT VARIABLE SHAPE")
print("-" * 100)

if variables:
    first = variables[0]
    print(f"TYPE: {type(first).__module__}.{type(first).__name__}")
    print("PUBLIC ATTRIBUTES:")
    print(", ".join(public_attrs(first)))
    print()
    print(f"FIRST VARIABLE REPR: {first!r}")
else:
    print("NO VARIABLES WERE GENERATED.")

print()

# ---------------------------------------------------------------------------
# 7. ACTUAL VARIABLES BY REQUIREMENT
# ---------------------------------------------------------------------------
actual_by_requirement = defaultdict(list)

for variable in variables:
    requirement_id = getattr(
        variable,
        "lesson_requirement_id",
        getattr(variable, "requirement_id", None),
    )
    actual_by_requirement[requirement_id].append(variable)

print("7. ACTUAL VARIABLES BY REQUIREMENT")
print("-" * 100)

total_weekly = 0
zero_variable_requirements = []

for req in db_requirements:
    subject = getattr(req, "subject", None)
    code = str(getattr(subject, "code", "") or "").strip().upper()
    weekly = getattr(
        req,
        "periods_per_week",
        getattr(req, "lessons_per_week", 0),
    )

    actual = actual_by_requirement.get(req.id, [])
    total_weekly += int(weekly or 0)

    if not actual:
        zero_variable_requirements.append(req)

    teacher_ids = {
        str(getattr(v, "teacher_id", ""))
        for v in actual
        if getattr(v, "teacher_id", None) is not None
    }
    period_ids = {
        str(getattr(v, "period_id", ""))
        for v in actual
        if getattr(v, "period_id", None) is not None
    }
    room_ids = {
        str(getattr(v, "room_id", ""))
        for v in actual
        if getattr(v, "room_id", None) is not None
    }
    days = {
        str(getattr(v, "day", ""))
        for v in actual
        if getattr(v, "day", None) is not None
    }

    print(
        f"{code:8} "
        f"REQ={req.id} "
        f"GROUP={req.instructional_group_id} "
        f"WEEK={weekly} "
        f"VARS={len(actual)} "
        f"TEACHERS={len(teacher_ids)} "
        f"DAYS={len(days)} "
        f"PERIODS={len(period_ids)} "
        f"ROOMS={len(room_ids)}"
    )

print()

# ---------------------------------------------------------------------------
# 8. REQUIREMENT COVERAGE
# ---------------------------------------------------------------------------
db_ids = {req.id for req in db_requirements}
generated_ids = set(actual_by_requirement)

missing_ids = db_ids - generated_ids
unexpected_ids = generated_ids - db_ids

print("8. HARD REQUIREMENT COVERAGE")
print("-" * 100)
print(f"DATABASE REQUIREMENTS:       {len(db_ids)}")
print(f"VARIABLE REQUIREMENT KEYS:   {len(generated_ids)}")
print(f"MISSING REQUIREMENT KEYS:    {len(missing_ids)}")
print(f"UNEXPECTED REQUIREMENT KEYS: {len(unexpected_ids)}")
print(f"DOMAIN WEEKLY TOTAL:         {total_weekly}")
print(f"ACTUAL VARIABLE COUNT:       {len(variables)}")
print()

if missing_ids:
    print("FAIL: REQUIREMENTS WITH ZERO GENERATED VARIABLES")
    for req in db_requirements:
        if req.id in missing_ids:
            subject = getattr(req, "subject", None)
            code = str(getattr(subject, "code", "") or "").strip().upper()
            weekly = getattr(
                req,
                "periods_per_week",
                getattr(req, "lessons_per_week", "?"),
            )
            print(
                f"  {code} REQ={req.id} "
                f"GROUP={req.instructional_group_id} WEEK={weekly}"
            )
else:
    print("PASS: EVERY DATABASE REQUIREMENT HAS GENERATED VARIABLES.")

print()

# ---------------------------------------------------------------------------
# 9. VARIABLE SAMPLE — PROVES WHAT DIMENSIONS ARE ACTUALLY GENERATED
# ---------------------------------------------------------------------------
print("9. VARIABLE SAMPLE")
print("-" * 100)

for variable in variables[:25]:
    fields = [
        "lesson_requirement_id",
        "teacher_id",
        "period_id",
        "room_id",
        "day",
        "slot_id",
    ]
    rendered = []
    for field in fields:
        if hasattr(variable, field):
            rendered.append(f"{field}={getattr(variable, field)!r}")
    print(" | ".join(rendered))

print()

# ---------------------------------------------------------------------------
# 10. AUTHORITATIVE CONCLUSION
# ---------------------------------------------------------------------------
print("10. AUTHORITATIVE CONCLUSION")
print("-" * 100)

if not missing_ids and not unexpected_ids:
    print("PASS: ALL ACTIVE DATABASE REQUIREMENTS REACH THE ACTUAL VARIABLE GENERATOR.")
else:
    print("FAIL: REQUIREMENT COVERAGE IS LOST AT OR BEFORE VARIABLE GENERATION.")

print()
print("THIS TRACE:")
print("- DID invoke the real variable-generation function.")
print("- DID create in-memory CP-SAT variables.")
print("- DID NOT call CpSolver.solve().")
print("- DID NOT persist a timetable.")
print("- DID NOT modify database records.")
print("- DID NOT modify solver source code.")
print("- DID NOT modify frontend code.")
print()
print("=" * 100)
print("ACTUAL VARIABLE GENERATION TRACE v2 COMPLETE")
print("=" * 100)