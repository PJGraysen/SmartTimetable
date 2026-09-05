import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.apps import apps


AUTHORITY = [
    ("Form", 4, "E", "Form 4E"),
    ("Form", 4, "W", "Form 4W"),
    ("Form", 3, "E", "Form 3E"),
    ("Form", 3, "W", "Form 3W"),
    ("Grade", 10, "E", "Grade 10E"),
    ("Grade", 10, "W", "Grade 10W"),
    ("Grade", 9, "E", "Grade 9E"),
    ("Grade", 9, "W", "Grade 9W"),
    ("Grade", 8, "E", "Grade 8E"),
    ("Grade", 8, "W", "Grade 8W"),
]


def fields(model):
    return [field.name for field in model._meta.get_fields()]


def describe(model_name):
    try:
        model = apps.get_model("academics", model_name)
    except Exception as exc:
        print(f"MODEL academics.{model_name}: ERROR {exc!r}")
        return None

    print()
    print(f"MODEL academics.{model_name}")
    print(f"TABLE {model._meta.db_table}")
    print("FIELDS " + ", ".join(fields(model)))

    try:
        print(f"COUNT {model.objects.count()}")
    except Exception as exc:
        print(f"COUNT ERROR {exc!r}")

    return model


print("=== AUTHORITATIVE CLASS CATALOGUE ===")
for _, _, _, label in AUTHORITY:
    print(label)

print()
print("=== MODEL STRUCTURE ===")

Grade = describe("Grade")
Stream = describe("Stream")
TeachingGroup = describe("TeachingGroup")
InstructionalGroup = describe("InstructionalGroup")
LessonRequirement = describe("LessonRequirement")

print()
print("=== CURRENT DATABASE POPULATION ===")

for model_name in (
    "Grade",
    "Stream",
    "TeachingGroup",
    "InstructionalGroup",
    "LessonRequirement",
):
    try:
        model = apps.get_model("academics", model_name)
        print(
            f"{model_name}: {model.objects.count()}"
        )
    except Exception as exc:
        print(
            f"{model_name}: ERROR {exc!r}"
        )

print()
print("=== CURRENT GRADE RECORDS ===")

try:
    for row in Grade.objects.all():
        print(
            f"PK={row.pk!r} "
            f"STR={str(row)!r} "
            f"DICT={row.__dict__!r}"
        )
except Exception as exc:
    print(f"ERROR {exc!r}")

print()
print("=== CURRENT STREAM RECORDS ===")

try:
    for row in Stream.objects.all():
        print(
            f"PK={row.pk!r} "
            f"STR={str(row)!r} "
            f"DICT={row.__dict__!r}"
        )
except Exception as exc:
    print(f"ERROR {exc!r}")

print()
print("=== CURRENT TEACHING GROUP RECORDS ===")

try:
    for row in TeachingGroup.objects.all():
        print(
            f"PK={row.pk!r} "
            f"STR={str(row)!r} "
            f"DICT={row.__dict__!r}"
        )
except Exception as exc:
    print(f"ERROR {exc!r}")

print()
print("=== CURRENT INSTRUCTIONAL GROUP RECORDS ===")

try:
    for row in InstructionalGroup.objects.all():
        print(
            f"PK={row.pk!r} "
            f"STR={str(row)!r} "
            f"DICT={row.__dict__!r}"
        )
except Exception as exc:
    print(f"ERROR {exc!r}")

print()
print("=== CURRENT LESSON REQUIREMENT COUNTS BY INSTRUCTIONAL GROUP ===")

try:
    group_field = None

    for field in LessonRequirement._meta.get_fields():
        name = field.name.lower()

        if (
            "instructional" in name
            or "teaching_group" in name
            or "group" in name
        ):
            group_field = field.name
            break

    print(f"GROUP FIELD: {group_field}")

    if group_field:
        values = (
            LessonRequirement.objects
            .values(group_field)
            .order_by(group_field)
        )

        for value in values:
            group_id = value.get(group_field)

            try:
                count = LessonRequirement.objects.filter(
                    **{group_field: group_id}
                ).count()
            except Exception:
                count = "ERROR"

            print(
                f"GROUP={group_id!r} "
                f"LESSON_REQUIREMENTS={count}"
            )

except Exception as exc:
    print(f"ERROR {exc!r}")

print()
print("=== AUTHORITATIVE TARGET ===")

print("TARGET STREAMS: 10")
print("TARGET ACTUAL WEEKLY LESSONS PER STREAM: 49")
print("TARGET ACTUAL WEEKLY LESSONS TOTAL: 490")
print("MONDAY ASSEMBLY: excluded from the 49 actual lessons")
print("SOLVER MODIFICATION: NONE")
print("DATABASE MODIFICATION: NONE")

print()
print("=== END ===")