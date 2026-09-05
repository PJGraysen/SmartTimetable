from __future__ import annotations

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from collections import defaultdict

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
print("SMARTTIMETABLE PRO - OPT1 VARIABLE GENERATION TRACE")
print("=" * 78)

print()
print("AUTHORITATIVE OPT1")
print("-" * 78)

block = get_grade10_parallel_block_for_subject("BIO")

print(f"BLOCK: {block.code}")
print(f"SUBJECTS: {block.subject_codes}")

print()
print("DATABASE REQUIREMENTS")
print("-" * 78)

database_requirements = list(
    LessonRequirement.objects
    .select_related("subject", "term")
    .filter(
        is_active=True,
        subject__code__in=("BIO", "MUS", "FRE"),
    )
    .order_by("instructional_group_id", "subject__code")
)

print(f"COUNT: {len(database_requirements)}")

print()
print("DOMAIN REQUIREMENTS")
print("-" * 78)

domain_requirements = list(
    load_lesson_requirements(database_requirements)
)

print(f"COUNT: {len(domain_requirements)}")

for requirement in domain_requirements:
    subject_code = str(
        getattr(requirement, "subject_code", "")
    ).strip().upper()

    print(
        f"{subject_code} | "
        f"REQ={requirement.id} | "
        f"GROUP={requirement.instructional_group_id} | "
        f"WEEK={requirement.periods_per_week} | "
        f"BLOCK={option_block_for_subject(subject_code)}"
    )

print()
print("VARIABLE MODULE")
print("-" * 78)

print(variables_module.__file__)

AssignmentVariable = variables_module.AssignmentVariable

print()
print("ASSIGNMENT VARIABLE FIELDS")
print("-" * 78)

for name in AssignmentVariable.__dataclass_fields__:
    print(name)

print()
print("IMPORTANT VARIABLE IDENTITY")
print("-" * 78)

print("Each solver variable carries:")
print("  lesson_requirement_id")
print("  teacher_id")
print("  instructional_group_id")
print("  period_id")
print("  day")
print("  room_id")
print("  cp-sat variable")

print()
print("OPT1 REQUIREMENT INDEX")
print("-" * 78)

opt1_ids = {
    requirement.id
    for requirement in domain_requirements
    if option_block_for_subject(
        str(requirement.subject_code).strip().upper()
    ) == block.subject_codes
}

print(f"OPT1 REQUIREMENT COUNT: {len(opt1_ids)}")

for requirement_id in sorted(opt1_ids, key=str):
    requirement = next(
        r for r in domain_requirements
        if r.id == requirement_id
    )

    print(
        f"{requirement.subject_code} | "
        f"{requirement.id} | "
        f"GROUP={requirement.instructional_group_id}"
    )

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
