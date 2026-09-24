from __future__ import annotations

import ast
import inspect
import os
import sys
from pathlib import Path
from collections import defaultdict
from uuid import UUID


PROJECT_ROOT = Path(r"C:\Projects\SmartTimetable")
BACKEND_ROOT = PROJECT_ROOT / "backend"
MODEL_PATH = (
    BACKEND_ROOT
    / "apps"
    / "scheduling"
    / "engine"
    / "solver"
    / "model.py"
)

TERM_ID = UUID("8ba158ac-4526-41d6-bf40-cb30023e09eb")

TARGET_METHODS = (
    "_add_grade10_option_block_constraints",
    "_add_grade10_cross_class_synchronization_constraints",
)

TARGET_SUBJECTS = {"BIO", "CHEM", "GEO", "BUS"}


def section(title: str):
    print("")
    print("=" * 72)
    print(title)
    print("=" * 72)


def diagnostic_error(message: str):
    print("")
    print(f"[DIAGNOSTIC ERROR] {message}")
    print("[INFO] No production change was made.")
    print("[INFO] No database write was performed.")
    print("[INFO] No solver solve() was called.")
    print("[INFO] Process remains non-terminating at the PowerShell level.")


print(f"ProjectRoot = {PROJECT_ROOT}")
print(f"BackendRoot = {BACKEND_ROOT}")
print(f"Production model = {MODEL_PATH}")

if not PROJECT_ROOT.exists():
    diagnostic_error(f"Project root missing: {PROJECT_ROOT}")
    sys.exit(0)

if not BACKEND_ROOT.exists():
    diagnostic_error(f"Backend root missing: {BACKEND_ROOT}")
    sys.exit(0)

if not MODEL_PATH.exists():
    diagnostic_error(f"Production model missing: {MODEL_PATH}")
    sys.exit(0)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

for path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


section("1. DJANGO / PRODUCTION PROBLEM")

try:
    import django
    django.setup()
    print(f"[PASS] Django {django.get_version()}")
except Exception as exc:
    diagnostic_error(f"Django setup failed: {type(exc).__name__}: {exc}")
    sys.exit(0)

try:
    from apps.core.models import Term
    from apps.scheduling.engine.infrastructure.django_loader import (
        DjangoSchedulingLoader,
    )
except Exception as exc:
    diagnostic_error(f"Production imports failed: {exc}")
    sys.exit(0)

try:
    term = Term.objects.get(id=TERM_ID)
    print(f"[PASS] Exact Term = {term}")
except Exception as exc:
    diagnostic_error(f"Term lookup failed: {exc}")
    sys.exit(0)

loader = DjangoSchedulingLoader()

try:
    problem = loader.load_problem(term=term)
    print("[PASS] Production SchedulingProblem loaded")
except Exception as exc:
    diagnostic_error(f"Production loader failed: {exc}")
    sys.exit(0)

print(f"Requirements = {len(problem.lesson_requirements)}")
print(f"Physical slots = {len(problem.slots)}")
print(f"Rooms = {len(problem.rooms)}")
print(f"Teachers = {len(problem.teachers)}")


section("2. PRODUCTION BUILDER")

try:
    from apps.scheduling.engine.solver.model import SolverModelBuilder
except Exception as exc:
    diagnostic_error(f"SolverModelBuilder import failed: {exc}")
    sys.exit(0)

builder = SolverModelBuilder()

try:
    print(f"build signature = {inspect.signature(builder.build)}")
except Exception as exc:
    diagnostic_error(f"build signature inspection failed: {exc}")
    sys.exit(0)


section("3. GRADE 10 BUSINESS CONTRACT")

groups = problem.instructional_group_by_id

grade10 = {}

for gid, group in groups.items():
    code = str(getattr(group, "code", "")).upper()
    if code in {"10E", "10W"}:
        grade10[code] = gid

if set(grade10) != {"10E", "10W"}:
    diagnostic_error(
        f"Expected 10E and 10W, found {sorted(grade10)}"
    )
    sys.exit(0)

requirements = {
    requirement.id: requirement
    for requirement in problem.lesson_requirements
}

for code in ("10E", "10W"):
    group_requirements = [
        r for r in problem.lesson_requirements
        if r.instructional_group_id == grade10[code]
        and r.is_active
    ]

    demand = sum(
        int(r.periods_per_week)
        for r in group_requirements
    )

    print(
        f"{code}: requirements={len(group_requirements)} "
        f"demand={demand}"
    )

print("")
print("BUSINESS CONTRACT TARGET:")
print("  10E = 84 periods/week")
print("  10W = 84 periods/week")
print("  Expected Grade 10 requirements = 20 per class")


section("4. SOURCE EXTRACTION — GRADE 10 METHODS")

source = MODEL_PATH.read_text(encoding="utf-8")
lines = source.splitlines()
tree = ast.parse(source)

found = {}

for node in ast.walk(tree):
    if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in TARGET_METHODS
    ):
        found[node.name] = node

for method_name in TARGET_METHODS:
    node = found.get(method_name)

    if node is None:
        print(f"[MISSING] {method_name}")
        continue

    end = getattr(node, "end_lineno", node.lineno)

    print("")
    print(
        f"################ {method_name} "
        f"({node.lineno}-{end}) ################"
    )

    for number in range(node.lineno, end + 1):
        print(
            f"{number:5}: {lines[number - 1]}"
        )


section("5. BUILD ORDER")

try:
    build_node = None

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "build"
        ):
            build_node = node
            break

    if build_node is not None:
        start = build_node.lineno
        end = getattr(build_node, "end_lineno", start)

        print(
            f"Production build() lines {start}-{end}"
        )

        for number in range(start, end + 1):
            text = lines[number - 1]

            if (
                "grade10" in text.lower()
                or "senior_school" in text.lower()
                or "simultaneous" in text.lower()
                or "group_clash" in text.lower()
                or "room_clash" in text.lower()
            ):
                print(
                    f"{number:5}: {text}"
                )

except Exception as exc:
    print(
        f"[WARN] Could not extract build order: {exc}"
    )


section("6. EXACT PRODUCTION BUILD — IN MEMORY ONLY")

try:
    solver_model = builder.build(problem=problem)
    print("[PASS] Production build completed")
except Exception as exc:
    diagnostic_error(
        f"Production build failed: {type(exc).__name__}: {exc}"
    )
    sys.exit(0)

variables = tuple(solver_model.variables)

print(f"AssignmentVariables = {len(variables)}")


section("7. IDENTIFY SUSPICIOUS GRADE 10 PAIRS")

grade10_variables = [
    v
    for v in variables
    if v.instructional_group_id
    in {grade10["10E"], grade10["10W"]}
]

print(
    f"Grade 10 AssignmentVariables = "
    f"{len(grade10_variables)}"
)

by_coordinate_subject = defaultdict(list)

for variable in grade10_variables:
    requirement = requirements.get(
        variable.lesson_requirement_id
    )

    if requirement is None:
        continue

    subject = str(
        getattr(requirement, "subject_code", "")
    ).upper()

    if subject not in TARGET_SUBJECTS:
        continue

    group_code = (
        "10E"
        if variable.instructional_group_id == grade10["10E"]
        else "10W"
    )

    key = (
        subject,
        str(variable.day),
        variable.period_id,
    )

    by_coordinate_subject[key].append(
        (group_code, variable, requirement)
    )

pairs = []

for key, entries in by_coordinate_subject.items():
    e = [
        item for item in entries
        if item[0] == "10E"
    ]

    w = [
        item for item in entries
        if item[0] == "10W"
    ]

    if len(e) == 1 and len(w) == 1:
        pairs.append(
            (
                key,
                e[0],
                w[0],
            )
        )

print(
    f"Suspicious subject/coordinate pairs = {len(pairs)}"
)

distribution = defaultdict(int)

for (
    (subject, day, period_id),
    _e,
    _w,
) in pairs:
    distribution[subject] += 1

for subject, count in sorted(distribution.items()):
    print(f"  {subject:5} = {count}")


section("8. FINAL CP CONSTRAINT PROVENANCE")

proto = solver_model.model.Proto()

cp_name_to_index = {
    variable.name: index
    for index, variable in enumerate(proto.variables)
}

assignment_by_cp_index = {}

for variable in grade10_variables:
    name = variable.variable.Name()

    if name in cp_name_to_index:
        assignment_by_cp_index[
            cp_name_to_index[name]
        ] = variable

print(
    f"Final CP variables = {len(proto.variables)}"
)

print(
    f"Final CP constraints = {len(proto.constraints)}"
)


def linear_data(constraint):
    if not constraint.HasField("linear"):
        return None

    return (
        list(constraint.linear.vars),
        list(constraint.linear.coeffs),
        list(constraint.linear.domain),
    )


pair_constraint_signatures = defaultdict(list)

for constraint_index, constraint in enumerate(
    proto.constraints
):
    data = linear_data(constraint)

    if data is None:
        continue

    var_indices, coeffs, domain = data

    if (
        len(var_indices) != 2
        or len(coeffs) != 2
        or domain != [0, 0]
        or sorted(coeffs) != [-1, 1]
    ):
        continue

    left = assignment_by_cp_index.get(
        var_indices[0]
    )
    right = assignment_by_cp_index.get(
        var_indices[1]
    )

    if left is None or right is None:
        continue

    if (
        left.instructional_group_id
        == right.instructional_group_id
    ):
        continue

    left_req = requirements.get(
        left.lesson_requirement_id
    )
    right_req = requirements.get(
        right.lesson_requirement_id
    )

    if left_req is None or right_req is None:
        continue

    left_subject = str(
        getattr(left_req, "subject_code", "")
    ).upper()

    right_subject = str(
        getattr(right_req, "subject_code", "")
    ).upper()

    if left_subject != right_subject:
        continue

    if left_subject not in TARGET_SUBJECTS:
        continue

    key = (
        left_subject,
        str(left.day),
        left.period_id,
    )

    pair_constraint_signatures[key].append(
        (
            constraint_index,
            left,
            right,
            left_req,
            right_req,
            coeffs,
            domain,
        )
    )


print(
    "Cross-group same-subject [1,-1] "
    "[0,0] constraints = "
    f"{sum(len(v) for v in pair_constraint_signatures.values())}"
)


section("9. REPRESENTATIVE PROVENANCE")

printed = set()

for (
    key,
    constraints,
) in sorted(
    pair_constraint_signatures.items(),
    key=lambda item: (
        item[0][0],
        item[0][1],
        str(item[0][2]),
    ),
):

    subject = key[0]

    if subject in printed:
        continue

    printed.add(subject)

    print("")
    print(
        f"TARGET SUBJECT = {subject}"
    )

    for (
        constraint_index,
        left,
        right,
        left_req,
        right_req,
        coeffs,
        domain,
    ) in constraints[:5]:

        print(
            f"  constraint index = {constraint_index}"
        )

        print(
            f"  domain = {domain}"
        )

        print(
            f"  coefficients = {coeffs}"
        )

        print(
            f"  10E requirement = "
            f"{left.lesson_requirement_id}"
        )

        print(
            f"  10W requirement = "
            f"{right.lesson_requirement_id}"
        )

        print(
            f"  10E teacher = "
            f"{left.teacher_id}"
        )

        print(
            f"  10W teacher = "
            f"{right.teacher_id}"
        )

        print(
            f"  day = {left.day}"
        )

        print(
            f"  period_id = {left.period_id}"
        )

        print(
            f"  10E CP variable = "
            f"{left.variable.Name()}"
        )

        print(
            f"  10W CP variable = "
            f"{right.variable.Name()}"
        )

        print("")

    if len(printed) >= 4:
        break


section("10. METHOD-SOURCE FINGERPRINT")

for method_name in TARGET_METHODS:
    node = found.get(method_name)

    if node is None:
        continue

    method_text = "\n".join(
        lines[node.lineno - 1:
              getattr(node, "end_lineno", node.lineno)]
    )

    fingerprints = {
        "instructional_group_id":
            method_text.count("instructional_group_id"),
        "add_at_most_one":
            method_text.count("add_at_most_one"),
        "model.add(":
            method_text.count("model.add("),
        "period_id":
            method_text.count("period_id"),
        "lesson_requirement_id":
            method_text.count("lesson_requirement_id"),
        "subject_code":
            method_text.count("subject_code"),
        "10E":
            method_text.count("10E"),
        "10W":
            method_text.count("10W"),
        "synchron":
            method_text.lower().count("synchron"),
        "equality":
            method_text.count("=="),
    }

    print("")
    print(method_name)

    for key, value in fingerprints.items():
        print(
            f"  {key:28} {value}"
        )


section("11. ROOT-CAUSE BOUNDARY")

print("")
print("[PASS] Variable generation was not modified.")
print("[PASS] TimetableSlot was not modified.")
print("[PASS] Curriculum requirements were not modified.")
print("[PASS] Database was not written.")
print("[PASS] CpSolver.solve() was not called.")
print("[PASS] GitHub was not accessed.")

print("")
print(
    "QUESTION BEING ANSWERED:"
)
print(
    "Which production Grade 10 constraint method creates "
    "the cross-group same-subject relationship that is "
    "contributing to the infeasibility / extra-lesson behavior?"
)

print("")
print(
    "V22 DIAGNOSTIC COMPLETE."
)
