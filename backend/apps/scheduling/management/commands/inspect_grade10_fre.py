from django.core.management.base import BaseCommand

from apps.academics.models import (
    InstructionalGroup,
    LessonRequirement,
    Subject,
)


class Command(BaseCommand):
    help = (
        "Read-only inspection of the Grade 10 FRE subject and "
        "lesson requirements."
    )

    def handle(self, *args, **options):
        self.stdout.write("=" * 76)
        self.stdout.write(
            "SMARTTIMETABLE PRO - GRADE 10 FRE DATABASE INSPECTION"
        )
        self.stdout.write("=" * 76)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        self.stdout.write("=== SUBJECT SEARCH ===")

        subjects = tuple(
            Subject.objects.all().order_by("id")
        )

        fre_subjects = []

        for subject in subjects:
            values = {
                str(getattr(subject, field, "") or "").upper()
                for field in (
                    "code",
                    "short_code",
                    "abbreviation",
                    "name",
                )
            }

            if "FRE" in values or any(
                "FRE" in value
                for value in values
                if value
            ):
                fre_subjects.append(subject)

        if not fre_subjects:
            self.stdout.write(
                "FAIL - No Subject matching FRE was found."
            )
        else:
            for subject in fre_subjects:
                self.stdout.write(
                    "FOUND SUBJECT:"
                )

                for field in (
                    "id",
                    "code",
                    "short_code",
                    "abbreviation",
                    "name",
                    "is_active",
                ):
                    if hasattr(subject, field):
                        self.stdout.write(
                            f"  {field}: "
                            f"{getattr(subject, field)}"
                        )

        self.stdout.write("")
        self.stdout.write("=== GRADE 10 FRE REQUIREMENTS ===")

        groups = tuple(
            InstructionalGroup.objects
            .filter(code__in=("10E", "10W"))
            .order_by("code")
        )

        for group in groups:
            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group.code} | {group.name}"
            )

            requirements = tuple(
                LessonRequirement.objects
                .filter(
                    instructional_group=group,
                )
                .select_related("subject")
            )

            matches = []

            for requirement in requirements:
                subject = getattr(requirement, "subject", None)

                if subject is None:
                    continue

                values = {
                    str(getattr(subject, field, "") or "").upper()
                    for field in (
                        "code",
                        "short_code",
                        "abbreviation",
                        "name",
                    )
                }

                if "FRE" in values or any(
                    "FRE" in value
                    for value in values
                    if value
                ):
                    matches.append(requirement)

            if not matches:
                self.stdout.write(
                    "  NO FRE LessonRequirement rows found."
                )
                continue

            for requirement in matches:
                self.stdout.write(
                    "  FRE REQUIREMENT:"
                )
                self.stdout.write(
                    f"    id: {requirement.id}"
                )
                self.stdout.write(
                    f"    active: "
                    f"{getattr(requirement, 'is_active', None)}"
                )
                self.stdout.write(
                    f"    lessons_per_week: "
                    f"{getattr(requirement, 'lessons_per_week', None)}"
                )

        self.stdout.write("")
        self.stdout.write("=== ALL SUBJECTS CONTAINING FRE ===")

        for subject in subjects:
            values = []

            for field in (
                "code",
                "short_code",
                "abbreviation",
                "name",
            ):
                value = getattr(subject, field, None)

                if value not in (None, ""):
                    values.append(
                        f"{field}={value}"
                    )

            if any(
                "FRE" in item.upper()
                for item in values
            ):
                self.stdout.write(
                    "  " + " | ".join(values)
                )

        self.stdout.write("")
        self.stdout.write("=" * 76)
        self.stdout.write(
            "INSPECTION COMPLETE - NO DATABASE CHANGES"
        )
        self.stdout.write("=" * 76)
