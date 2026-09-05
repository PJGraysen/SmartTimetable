import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.apps import apps

print("=" * 100)
print("SMARTTIMETABLE PRO - GRADE 10 ELECTIVE MODEL DISCOVERY")
print("READ ONLY - NO DATABASE CHANGES")
print("=" * 100)

# ---------------------------------------------------------------------
# 1. Discover potentially relevant models
# ---------------------------------------------------------------------
keywords = (
    "elective",
    "option",
    "choice",
    "selection",
    "subjectchoice",
    "subjectselection",
)

print("\n" + "-" * 100)
print("POTENTIALLY RELEVANT MODELS")
print("-" * 100)

relevant = []

for model in apps.get_models():
    name = model.__name__
    label = model._meta.label

    haystack = (name + " " + label).lower()

    if any(k in haystack for k in keywords):
        relevant.append(model)

if not relevant:
    print("No model names matched elective/option/choice/selection.")
else:
    for model in sorted(relevant, key=lambda m: m._meta.label):
        print(f"\nMODEL: {model._meta.label}")
        print("FIELDS:")

        for field in model._meta.get_fields():
            print(
                f"  {field.name:<30} "
                f"type={field.__class__.__name__:<25} "
                f"relation={getattr(field, 'related_model', None)}"
            )

# ---------------------------------------------------------------------
# 2. Subject model discovery
# ---------------------------------------------------------------------
print("\n" + "-" * 100)
print("SUBJECT MODELS")
print("-" * 100)

subject_models = []

for model in apps.get_models():
    haystack = (
        model.__name__ + " " + model._meta.label
    ).lower()

    if "subject" in haystack:
        subject_models.append(model)

for model in sorted(subject_models, key=lambda m: m._meta.label):
    print(f"\nMODEL: {model._meta.label}")

    fields = list(model._meta.get_fields())

    for field in fields:
        if hasattr(field, "attname"):
            print(
                f"  FIELD {field.name:<30} "
                f"type={field.__class__.__name__:<25}"
            )

    try:
        qs = model.objects.all()

        print(f"  RECORD COUNT: {qs.count()}")

        for obj in qs[:100]:
            values = []

            for field in fields:
                if not hasattr(field, "attname"):
                    continue

                try:
                    value = getattr(obj, field.name)
                except Exception:
                    continue

                if isinstance(value, (str, int, float, bool)) or value is None:
                    values.append(f"{field.name}={value!r}")

            print("   ", " | ".join(values))

    except Exception as exc:
        print(f"  Could not enumerate records: {exc}")

# ---------------------------------------------------------------------
# 3. Grade 10 LessonRequirements and assignments
# ---------------------------------------------------------------------
print("\n" + "-" * 100)
print("GRADE 10 ACTIVE LESSON REQUIREMENTS + TEACHER ASSIGNMENTS")
print("-" * 100)

try:
    LR = apps.get_model("academics", "LessonRequirement")
    TA = apps.get_model("scheduling", "TeacherAssignment")

    requirements = (
        LR.objects
        .filter(is_active=True)
        .select_related("instructional_group", "subject")
        .order_by(
            "instructional_group__name",
            "subject__name",
        )
    )

    for req in requirements:
        group = req.instructional_group
        group_name = str(group)

        if "10" not in group_name.upper():
            continue

        subject = req.subject
        subject_name = getattr(subject, "name", str(subject))

        print(
            f"\nGROUP={group_name}"
            f" | SUBJECT={subject_name}"
            f" | LESSONS={req.lessons_per_week}"
            f" | REQUIREMENT_ID={req.id}"
        )

        assignments = TA.objects.filter(
            lesson_requirement=req,
            is_active=True,
        )

        count = assignments.count()

        print(f"  ACTIVE ASSIGNMENTS: {count}")

        for assignment in assignments:
            teacher = getattr(assignment, "teacher", None)
            print(
                f"    TEACHER={teacher}"
                f" | ASSIGNMENT_ID={assignment.id}"
            )

except Exception as exc:
    print(f"Grade 10 requirement audit failed: {exc}")

# ---------------------------------------------------------------------
# 4. Search every model for fields whose names imply selection/option
# ---------------------------------------------------------------------
print("\n" + "-" * 100)
print("FIELDS SUGGESTING ELECTIVE/OPTION/SELECTION LOGIC")
print("-" * 100)

matches = []

for model in apps.get_models():
    for field in model._meta.get_fields():
        field_name = field.name.lower()

        if any(
            token in field_name
            for token in (
                "elective",
                "option",
                "choice",
                "selection",
                "selected",
            )
        ):
            matches.append(
                (
                    model._meta.label,
                    field.name,
                    field.__class__.__name__,
                )
            )

if not matches:
    print("No matching fields found.")
else:
    for model_name, field_name, field_type in sorted(matches):
        print(
            f"{model_name:<50} "
            f"{field_name:<35} "
            f"{field_type}"
        )

print("\n" + "=" * 100)
print("END OF READ-ONLY DISCOVERY")
print("=" * 100)