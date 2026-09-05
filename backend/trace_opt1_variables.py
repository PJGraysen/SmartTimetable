from __future__ import annotations

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.scheduling.models import LessonRequirement
from apps.scheduling.engine.application.grade10_parallel_blocks import (
    get_grade10_parallel_block_for_subject,
)
from apps.scheduling.engine.infrastructure.django_loader import (
    load_lesson_requirements,
)
from apps.scheduling.engine.solver.model import (
    option_block_for_subject,
)
from apps.scheduling.engine.solver import variables as variables_module


print("=" * 78)
print("SMARTTIMETABLE PRO - OPT1 VARIABLE / SOLVER TRACE")
print("=" * 78)

print()
print("AUTHORITATIVE OPT1")
print("-" * 78)

opt1 = get_grade10_parallel_block_for_subject("BIO")

print(f"BLOCK: {opt1.code}")
print(f"SUBJECTS: {opt1.subject_codes}")

print()
print("DATABASE → DOMAIN REQUIREMENTS")
print("-" * 78)

database_requirements = list(
    LessonRequirement.objects
    .select_related("subject", "term")
    .filter(
        is_active=True,
        subject__code__in=("BIO", "MUS", "FRE"),
    )
    .order_by("subject__code", "instructional_group_id")
)

print(
    f"DATABASE REQUIREMENTS: "
    f"{len(database_requirements)}"
)

domain_requirements = list(
    load_lesson_requirements(database_requirements)
)

print(
    f"DOMAIN REQUIREMENTS: "
    f"{len(domain_requirements)}"
)

print()
print("OPT1 DOMAIN REQUIREMENTS")
print("-" * 78)

for requirement in domain_requirements:

    subject_code = str(
        getattr(requirement, "subject_code", "")
    ).strip().upper()

    block = option_block_for_subject(subject_code)

    print()
    print(f"REQUIREMENT: {requirement.id}")
    print(f"SUBJECT: {subject_code}")
    print(
        f"GROUP: "
        f"{getattr(requirement, 'instructional_group_id', None)}"
    )
    print(
        f"PERIODS/WEEK: "
        f"{getattr(requirement, 'periods_per_week', None)}"
    )
    print(f"OPTION BLOCK: {block}")

print()
print("VARIABLE MODULE INSPECTION")
print("-" * 78)

print(
    "VARIABLE MODULE: "
    f"{variables_module.__file__}"
)

print()
print("ASSIGNMENT VARIABLE STRUCTURE")
print("-" * 78)

AssignmentVariable = getattr(
    variables_module,
    "AssignmentVariable",
    None,
)

if AssignmentVariable is None:

    print("AssignmentVariable NOT FOUND.")

else:

    print("AssignmentVariable annotations:")

    annotations = getattr(
        AssignmentVariable,
        "__annotations__",
        {},
    )

    for name, value in annotations.items():
        print(f"{name}: {value}")

    print()
    print("AssignmentVariable fields:")

    fields = getattr(
        AssignmentVariable,
        "__dataclass_fields__",
        {},
    )

    for name in fields:
        print(name)

print()
print("SOLVER MODEL OPTION-BLOCK FUNCTION")
print("-" * 78)

for subject_code in ("BIO", "MUS", "FRE"):

    block = option_block_for_subject(subject_code)

    print(
        f"{subject_code}: "
        f"{block}"
    )

print()
print("EXPECTED OPT1 CONTRACT")
print("-" * 78)

print("OPTION_1 = BIO / MUS / FRE")
print("Each active requirement = 5 periods/week.")
print("OPT1 subjects synchronize by exact day + period.")
print("Teacher assignments remain independent.")
print("French remains structurally present.")
print("French may remain inactive until an authoritative")
print("French teacher is assigned.")

print()
print("READ-ONLY GUARANTEE")
print("-" * 78)
print("No database records modified.")
print("No LessonRequirement records modified.")
print("No TeacherAssignment records modified.")
print("No timetable entries modified.")
print("No solver model modified.")

print()
print("=" * 78)
print("TRACE COMPLETE")
print("=" * 78)
