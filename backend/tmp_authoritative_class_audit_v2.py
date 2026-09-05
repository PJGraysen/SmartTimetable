from django.apps import apps

print()
print("=== ALL DJANGO MODELS ===")

for model in apps.get_models():
    print(model._meta.label)

print()
print("=== CLASS/GRADE/STREAM/GROUP MODELS ===")

keywords = (
    "class",
    "grade",
    "form",
    "stream",
    "section",
    "group",
)

candidate_models = []

for model in apps.get_models():
    fields = list(model._meta.get_fields())

    interesting = [
        field.name
        for field in fields
        if any(keyword in field.name.lower() for keyword in keywords)
    ]

    if not interesting:
        continue

    candidate_models.append(model)

    print()
    print(f"MODEL: {model._meta.label}")
    print(f"TABLE: {model._meta.db_table}")
    print("FIELDS:", ", ".join(interesting))

    try:
        queryset = model.objects.all()
        print("COUNT:", queryset.count())

        for row in queryset[:100]:
            values = []

            for field_name in interesting:
                try:
                    value = getattr(row, field_name)

                    if hasattr(value, "all") and callable(value.all):
                        try:
                            value = list(value.all())
                        except Exception:
                            pass

                    values.append(f"{field_name}={value!r}")
                except Exception as exc:
                    values.append(
                        f"{field_name}=<ERROR {exc!r}>"
                    )

            print("  " + " | ".join(values))

    except Exception as exc:
        print("  [QUERY ERROR]", repr(exc))

print()
print("=== LIKELY AUTHORITATIVE ACADEMICS MODELS ===")

for model in apps.get_models():
    if model._meta.app_label != "academics":
        continue

    if model.__name__ in (
        "Grade",
        "Stream",
        "TeachingGroup",
        "InstructionalGroup",
        "LessonRequirement",
    ):
        print()
        print(f"MODEL: {model._meta.label}")
        print(f"TABLE: {model._meta.db_table}")

        for field in model._meta.get_fields():
            relation = getattr(field, "related_model", None)

            print(
                f"  FIELD={field.name}"
                f" | TYPE={field.__class__.__name__}"
                f" | RELATED={relation}"
            )

print()
print("=== SCHEDULING MODELS ===")

for model in apps.get_models():
    if model._meta.app_label != "scheduling":
        continue

    print()
    print(f"MODEL: {model._meta.label}")
    print(f"TABLE: {model._meta.db_table}")

    for field in model._meta.get_fields():
        relation = getattr(field, "related_model", None)

        print(
            f"  FIELD={field.name}"
            f" | TYPE={field.__class__.__name__}"
            f" | RELATED={relation}"
        )

print()
print("=== CURRENT ACADEMICS ROW COUNTS ===")

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
            f"{model._meta.label}: "
            f"{model.objects.count()}"
        )
    except Exception as exc:
        print(
            f"academics.{model_name}: "
            f"[ERROR {exc!r}]"
        )

print()
print("=== EXACT GRADE ROWS ===")

try:
    Grade = apps.get_model("academics", "Grade")

    for row in Grade.objects.all().order_by("id"):
        print(
            f"id={row.pk!r} | "
            f"{row!r} | "
            f"dict={row.__dict__!r}"
        )
except Exception as exc:
    print("ERROR:", repr(exc))

print()
print("=== EXACT STREAM ROWS ===")

try:
    Stream = apps.get_model("academics", "Stream")

    for row in Stream.objects.all().order_by("id"):
        print(
            f"id={row.pk!r} | "
            f"{row!r} | "
            f"dict={row.__dict__!r}"
        )
except Exception as exc:
    print("ERROR:", repr(exc))

print()
print("=== EXACT TEACHING GROUP ROWS ===")

try:
    TeachingGroup = apps.get_model(
        "academics",
        "TeachingGroup",
    )

    for row in TeachingGroup.objects.all().order_by("id"):
        print(
            f"id={row.pk!r} | "
            f"{row!r} | "
            f"dict={row.__dict__!r}"
        )
except Exception as exc:
    print("ERROR:", repr(exc))

print()
print("=== EXACT INSTRUCTIONAL GROUP ROWS ===")

try:
    InstructionalGroup = apps.get_model(
        "academics",
        "InstructionalGroup",
    )

    for row in InstructionalGroup.objects.all().order_by("id"):
        print(
            f"id={row.pk!r} | "
            f"{row!r} | "
            f"dict={row.__dict__!r}"
        )
except Exception as exc:
    print("ERROR:", repr(exc))

print()
print("=== EXACT LESSON REQUIREMENT ROWS ===")

try:
    LessonRequirement = apps.get_model(
        "academics",
        "LessonRequirement",
    )

    print(
        "TOTAL:",
        LessonRequirement.objects.count()
    )

    for row in LessonRequirement.objects.all().order_by("id")[:200]:
        print(
            f"id={row.pk!r} | "
            f"{row!r} | "
            f"dict={row.__dict__!r}"
        )
except Exception as exc:
    print("ERROR:", repr(exc))

print()
print("=== AUDIT COMPLETE ===")
