import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.scheduling.engine.application.grade10_parallel_blocks import (
    get_grade10_parallel_block_for_subject,
)
from apps.scheduling.engine.infrastructure.django_loader import (
    load_lesson_requirements,
)
from apps.scheduling.models import LessonRequirement


print("=" * 78)
print("SMARTTIMETABLE PRO - OPT1 DATABASE → DOMAIN REQUIREMENT TRACE")
print("=" * 78)

print()
print("AUTHORITATIVE OPT1")
print("-" * 78)

block = get_grade10_parallel_block_for_subject("BIO")

print(f"BLOCK: {block.code}")
print(f"SUBJECTS: {block.subject_codes}")

print()
print("DATABASE LESSON REQUIREMENTS")
print("-" * 78)

requirements = (
    LessonRequirement.objects
    .select_related("subject", "term")
    .filter(
        is_active=True,
        subject__code__in=("BIO", "MUS", "FRE"),
    )
    .order_by("subject__code")
)

rows = list(requirements)

print(f"TOTAL ACTIVE BIO/MUS/FRE REQUIREMENTS: {len(rows)}")

if not rows:
    print("NO ACTIVE BIO/MUS/FRE LESSON REQUIREMENTS FOUND.")

for requirement in rows:
    subject_code = (
        getattr(requirement.subject, "code", None)
        if requirement.subject is not None
        else None
    )

    print()
    print(f"ID: {requirement.id}")
    print(f"SUBJECT: {subject_code}")
    print(f"TERM: {requirement.term_id}")
    print(f"INSTRUCTIONAL GROUP: {getattr(requirement, 'instructional_group_id', None)}")
    print(f"WEEKLY PERIODS: {getattr(requirement, 'weekly_periods', None)}")
    print(f"ACTIVE: {requirement.is_active}")

print()
print("EXPECTED OPT1 MEMBERSHIP")
print("-" * 78)

found = { 
    getattr(r.subject, "code", "").strip().upper()
    for r in rows
    if getattr(r, "subject", None) is not None
}

for subject_code in ("BIO", "MUS", "FRE"):
    print(
        f"{subject_code}: "
        f"{'FOUND' if subject_code in found else 'MISSING'}"
    )

print()
print("IMPORTANT")
print("-" * 78)
print("This trace is READ-ONLY.")
print("No LessonRequirement records are modified.")
print("No TeacherAssignment records are modified.")
print("No timetable entries are modified.")
print("No solver model is modified.")

print()
print("=" * 78)
print("TRACE COMPLETE")
print("=" * 78)
