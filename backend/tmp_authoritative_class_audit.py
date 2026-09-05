from pathlib import Path
from django.apps import apps

print("\n=== ALL DJANGO MODELS ===")

for model in apps.get_models():
    print(f"{model._meta.label}")

print("\n=== MODELS WITH CLASS/GRADE/STREAM/FORMS ===")

keywords = (
    "class",
    "grade",
    "form",
    "stream",
    "section",
    "group",
)

for model in apps.get_models():
    fields = list(model._meta.get_fields())

    interesting = [
        field.name
        for field in fields
        if any(keyword in field.name.lower() for keyword in keywords)
    ]

    if not interesting:
        continue

    print()
    print(f"MODEL: {model._meta.label}")
    print("TABLE:", model._meta.db_table)
    print("FIELDS:", ", ".join(interesting))

    try:
        queryset = model.objects.all()
        print("COUNT:", queryset.count())

        for row in queryset[:100]:
            values = []

            for field_name in interesting:
                try:
                    value = getattr(row, field_name)
                    values.append(f"{field_name}={value!r}")
                except Exception as exc:
                    values.append(f"{field_name}=<ERROR {exc}>")

            print("  " + " | ".join(values))

    except Exception as exc:
        print("  [QUERY ERROR]", repr(exc))

print("\n=== SCHEDULING MODELS ===")

for model in apps.get_models():
    label = model._meta.label.lower()

    if "schedul" not in label and "timetable" not in label:
        continue

    print()
    print(f"MODEL: {model._meta.label}")
    print("TABLE:", model._meta.db_table)

    for field in model._meta.get_fields():
        print(
            f"  {field.name}: "
            f"{getattr(field, 'related_model', None)}"
        )

print("\n=== INSTALLED APPS ===")

for config in apps.get_app_configs():
    print(config.name)

print("\n=== AUDIT COMPLETE ===")
