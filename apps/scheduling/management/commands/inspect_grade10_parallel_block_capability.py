from django.core.management.base import BaseCommand
from django.apps import apps


class Command(BaseCommand):
    help = "Read-only audit of Grade 10 parallel elective block capability."

    BLOCKS = {
        "OPTION_1": ("BIO", "MUS", "FRE"),
        "OPTION_2": ("CHEM", "PHY", "LIT"),
        "OPTION_3": ("GEO", "HIS", "CS"),
        "OPTION_4": ("BUS", "AGR"),
    }

    def handle(self, *args, **options):
        print("=" * 88)
        print("SMARTTIMETABLE PRO - GRADE 10 PARALLEL BLOCK CAPABILITY AUDIT")
        print("=" * 88)
        print()
        print("READ-ONLY: NO DATABASE CHANGES WILL BE MADE.")
        print()

        print("AUTHORITATIVE PARALLEL BLOCKS")
        print("-" * 88)

        for block, subjects in self.BLOCKS.items():
            print(
                f"{block}: {' / '.join(subjects)} = "
                f"5 SHARED TIMETABLE SLOTS/WEEK"
            )

        print()
        print("MODEL INVENTORY")
        print("-" * 88)

        models = list(apps.get_models())

        for model in models:
            label = model._meta.label
            name = model.__name__.lower()

            if any(
                token in name
                for token in (
                    "lesson",
                    "timetable",
                    "teacher",
                    "subject",
                    "instructional",
                    "period",
                    "activity",
                    "break",
                    "resource",
                    "room",
                )
            ):
                print(f"{label}")
                for field in model._meta.fields:
                    print(
                        f"    {field.name:<32} "
                        f"{field.__class__.__name__:<28} "
                        f"relation={getattr(field, 'related_model', None)}"
                    )

                for field in model._meta.many_to_many:
                    print(
                        f"    {field.name:<32} "
                        f"{field.__class__.__name__:<28} "
                        f"relation={getattr(field.remote_field, 'model', None)}"
                    )

                print()

        print("=" * 88)
        print("PARALLEL SLOT REPRESENTATION CHECK")
        print("=" * 88)

        try:
            TimetableEntry = apps.get_model(
                "scheduling",
                "TimetableEntry",
            )
        except LookupError:
            TimetableEntry = None

        if TimetableEntry is None:
            print("RESULT: TimetableEntry model was not found.")
        else:
            print("TimetableEntry model found.")
            print()

            fields = {
                f.name: f
                for f in TimetableEntry._meta.get_fields()
            }

            for name in (
                "day",
                "period",
                "period_number",
                "lesson_requirement",
                "teacher",
                "room",
                "resource",
                "instructional_group",
            ):
                if name in fields:
                    field = fields[name]
                    print(
                        f"FOUND  {name:<24} "
                        f"{field.__class__.__name__}"
                    )
                else:
                    print(f"ABSENT {name:<24}")

        print()
        print("=" * 88)
        print("GRADE 10 SUBJECT REQUIREMENT CAPABILITY")
        print("=" * 88)

        try:
            LessonRequirement = apps.get_model(
                "academics",
                "LessonRequirement",
            )
        except LookupError:
            LessonRequirement = None

        if LessonRequirement is None:
            print("RESULT: LessonRequirement model was not found.")
        else:
            print("LessonRequirement model found.")

            for field in LessonRequirement._meta.get_fields():
                print(
                    f"    {field.name:<32} "
                    f"{field.__class__.__name__:<28} "
                    f"relation={getattr(field, 'related_model', None)}"
                )

        print()
        print("=" * 88)
        print("AUTHORITATIVE INTERPRETATION")
        print("=" * 88)
        print()
        print("Each elective subject remains an independent requirement.")
        print("Subjects in the same option block share the SAME:")
        print("    DAY")
        print("    PERIOD")
        print("    TIME SLOT")
        print()
        print("They remain independently identifiable by:")
        print("    SUBJECT")
        print("    SUBJECT CODE")
        print("    INSTRUCTIONAL GROUP")
        print("    TEACHER")
        print("    ROOM / RESOURCE")
        print()
        print("Example:")
        print("    OPTION_1 slot -> BIO/T016")
        print("                  -> MUS/T019")
        print("                  -> FRE/<inactive/no teacher>")
        print()
        print("This audit does NOT create elective blocks.")
        print("This audit does NOT modify LessonRequirements.")
        print("This audit does NOT modify teachers.")
        print("This audit does NOT modify timetable entries.")
        print("This audit does NOT modify the solver.")
        print("This audit does NOT modify the frontend.")
        print()
        print("=" * 88)
        print("END READ-ONLY PARALLEL BLOCK CAPABILITY AUDIT")
        print("=" * 88)
