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
print("SMARTTIMETABLE PRO - OPT1 DJANGO LOADER TRACE")
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

queryset = (
    LessonRequirement.objects
    .select_related("subject", "term")
    .filter(
        is_active=True,
        subject__code__in=("BIO", "MUS", "FRE"),
    )
    .order_by("subject__code", "instructional_group_id")
)

database_requirements = list(queryset)

print(f"DATABASE COUNT: {len(database_requirements)}")

print()
print("LOADER INVOCATION")
print("-" * 78)

try:
    loaded = load_lesson_requirements(database_requirements)
except TypeError as exc:
    print("LOADER CALL FAILED:")
    print(exc)
    print()
    print("The loader signature does not accept the queryset in this form.")
    print("No application code was modified.")
    raise

loaded = list(loaded)

print(f"DOMAIN REQUIREMENT COUNT: {len(loaded)}")

print()
print("DOMAIN REQUIREMENTS")
print("-" * 78)

for requirement in loaded:

    subject_code = getattr(
        requirement,
        "subject_code",
        None,
    )

    instructional_group_id = getattr(
        requirement,
        "instructional_group_id",
        None,
    )

    weekly_count = None

    for field_name in (
        "weekly_periods",
        "weekly_lessons",
        "periods_per_week",
        "lessons_per_week",
        "weekly_frequency",
        "required_periods",
    ):
        if hasattr(requirement, field_name):
            weekly_count = getattr(
                requirement,
                field_name,
            )
            print(
                f"FOUND WEEKLY FIELD: "
                f"{field_name}={weekly_count}"
            )
            break

    block_for_subject = (
        get_grade10_parallel_block_for_subject(subject_code)
        if subject_code
        else None
    )

    print()
    print(f"ID: {getattr(requirement, 'id', None)}")
    print(f"SUBJECT CODE: {subject_code}")
    print(f"INSTRUCTIONAL GROUP: {instructional_group_id}")
    print(f"WEEKLY VALUE: {weekly_count}")
    print(
        "OPT1 BLOCK: "
        f"{block_for_subject.code if block_for_subject else None}"
    )

print()
print("OPT1 DOMAIN COVERAGE")
print("-" * 78)

domain_subjects = {
    str(getattr(r, "subject_code", "")).strip().upper()
    for r in loaded
}

for subject_code in ("BIO", "MUS", "FRE"):
    print(
        f"{subject_code}: "
        f"{'FOUND' if subject_code in domain_subjects else 'MISSING'}"
    )

print()
print("GROUP COVERAGE")
print("-" * 78)

for subject_code in ("BIO", "MUS", "FRE"):
    matches = [
        r for r in loaded
        if str(
            getattr(r, "subject_code", "")
        ).strip().upper() == subject_code
    ]

    groups = {
        str(getattr(r, "instructional_group_id", None))
        for r in matches
    }

    print(
        f"{subject_code}: "
        f"{len(matches)} requirement(s), "
        f"{len(groups)} instructional group(s)"
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
