from django.apps import apps
from django.db.models import Q

print("")
print("=" * 90)
print("SMARTTIMETABLE PRO - GRADE 10 GENERATION INPUT AUDIT")
print("READ ONLY - NO DATABASE CHANGES")
print("=" * 90)

# ---------------------------------------------------------------------------
# Locate models dynamically so this audit does not assume an incorrect
# module location for Period or related scheduling models.
# ---------------------------------------------------------------------------

def find_model(model_name):
    matches = []
    for model in apps.get_models():
        if model.__name__.lower() == model_name.lower():
            matches.append(model)
    return matches

LessonRequirement = None
TeacherAssignment = None

lr_matches = find_model("LessonRequirement")
ta_matches = find_model("TeacherAssignment")

if lr_matches:
    LessonRequirement = lr_matches[0]

if ta_matches:
    TeacherAssignment = ta_matches[0]

print("")
print("MODEL DISCOVERY")
print("-" * 90)
print("LessonRequirement:", LessonRequirement)
print("TeacherAssignment:", TeacherAssignment)

# ---------------------------------------------------------------------------
# Academic / instructional-group models
# ---------------------------------------------------------------------------

print("")
print("AVAILABLE INSTRUCTIONAL-GROUP MODELS")
print("-" * 90)

for model in apps.get_models():
    if "group" in model.__name__.lower():
        print(
            model._meta.label,
            "fields=",
            [f.name for f in model._meta.fields],
        )

# ---------------------------------------------------------------------------
# Period models
# ---------------------------------------------------------------------------

print("")
print("AVAILABLE PERIOD MODELS")
print("-" * 90)

period_models = []

for model in apps.get_models():
    if "period" in model.__name__.lower():
        period_models.append(model)
        print(
            model._meta.label,
            "fields=",
            [f.name for f in model._meta.fields],
        )

# ---------------------------------------------------------------------------
# Print Grade 10 LessonRequirements.
# ---------------------------------------------------------------------------

print("")
print("GRADE 10 LESSON REQUIREMENTS")
print("-" * 90)

if LessonRequirement is None:
    print("LessonRequirement model could not be located.")
else:
    qs = LessonRequirement.objects.all()

    print("TOTAL LessonRequirements:", qs.count())

    for obj in qs:
        values = {}

        for field in obj._meta.fields:
            try:
                value = getattr(obj, field.name)
            except Exception:
                value = "<ERROR>"

            values[field.name] = str(value)

        text = " ".join(str(v) for v in values.values()).lower()

        if "grade 10" in text or "10e" in text or "10w" in text:
            print("")
            print("ID:", getattr(obj, "id", None))
            print("FIELDS:")

            for key, value in values.items():
                print(f"  {key}: {value}")

# ---------------------------------------------------------------------------
# Specifically locate FRE and GST.
# ---------------------------------------------------------------------------

print("")
print("FRE / GST REQUIREMENTS")
print("-" * 90)

if LessonRequirement is not None:
    for obj in LessonRequirement.objects.all():
        values = {}

        for field in obj._meta.fields:
            try:
                values[field.name] = str(getattr(obj, field.name))
            except Exception:
                values[field.name] = "<ERROR>"

        text = " ".join(values.values()).lower()

        if (
            "fre" in text
            or "french" in text
            or "gst" in text
            or "group study" in text
            or "life skills" in text
        ):
            print("")
            print("ID:", getattr(obj, "id", None))

            for key, value in values.items():
                print(f"  {key}: {value}")

# ---------------------------------------------------------------------------
# Teacher assignments related to FRE/GST.
# ---------------------------------------------------------------------------

print("")
print("FRE / GST TEACHER ASSIGNMENTS")
print("-" * 90)

if TeacherAssignment is None:
    print("TeacherAssignment model could not be located.")
else:
    qs = TeacherAssignment.objects.all()

    print("TOTAL TeacherAssignments:", qs.count())

    for obj in qs:
        values = {}

        for field in obj._meta.fields:
            try:
                values[field.name] = str(getattr(obj, field.name))
            except Exception:
                values[field.name] = "<ERROR>"

        text = " ".join(values.values()).lower()

        if (
            "fre" in text
            or "french" in text
            or "gst" in text
            or "group study" in text
            or "life skills" in text
        ):
            print("")
            print("ID:", getattr(obj, "id", None))

            for key, value in values.items():
                print(f"  {key}: {value}")

# ---------------------------------------------------------------------------
# Period data.
# ---------------------------------------------------------------------------

print("")
print("PERIOD CONFIGURATION")
print("-" * 90)

for PeriodModel in period_models:
    print("")
    print("MODEL:", PeriodModel._meta.label)

    try:
        qs = PeriodModel.objects.all()

        print("TOTAL PERIOD ROWS:", qs.count())

        for obj in qs.order_by("id"):
            values = {}

            for field in obj._meta.fields:
                try:
                    values[field.name] = str(getattr(obj, field.name))
                except Exception:
                    values[field.name] = "<ERROR>"

            print(
                "  ",
                " | ".join(
                    f"{key}={value}"
                    for key, value in values.items()
                )
            )

    except Exception as exc:
        print("ERROR READING PERIOD MODEL:", repr(exc))

# ---------------------------------------------------------------------------
# Summary of the expected contract versus observed diagnostic values.
# ---------------------------------------------------------------------------

print("")
print("=" * 90)
print("CONTRACT CROSS-CHECK")
print("=" * 90)

print("Expected weekly teaching lessons per group : 49")
print("Expected Grade 10 instructional groups     : 10E, 10W")
print("Expected FRE requirement per group        : 5")
print("Expected GST/LF requirement per group     : 1")
print("")
print("Solver diagnostic currently reports:")
print("10E required periods                      : 84")
print("10E available group slots                : 10")
print("10W required periods                      : 84")
print("10W available group slots                : 10")

print("")
print("=" * 90)
print("END GRADE 10 GENERATION INPUT AUDIT")
print("=" * 90)