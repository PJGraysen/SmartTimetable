from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academics.models import InstructionalGroup, LessonRequirement, Subject


class Command(BaseCommand):
    help = "Activate the existing Grade 10 FRE requirements for 10E and 10W."

    def handle(self, *args, **options):
        self.stdout.write("=" * 76)
        self.stdout.write("SMARTTIMETABLE PRO - ACTIVATE GRADE 10 FRE")
        self.stdout.write("=" * 76)
        self.stdout.write("TARGET: Existing FRE requirements only")
        self.stdout.write("")

        subject = Subject.objects.filter(code="FRE").first()

        if subject is None:
            raise CommandError("FRE subject was not found.")

        groups = tuple(
            InstructionalGroup.objects
            .filter(code__in=("10E", "10W"))
            .order_by("code")
        )

        if {str(group.code) for group in groups} != {"10E", "10W"}:
            raise CommandError(
                "Expected exactly Grade 10E and Grade 10W groups."
            )

        targets = []

        for group in groups:
            requirements = tuple(
                LessonRequirement.objects.filter(
                    instructional_group=group,
                    subject=subject,
                ).order_by("id")
            )

            if len(requirements) != 1:
                raise CommandError(
                    f"{group.code}: expected exactly one FRE requirement; "
                    f"found {len(requirements)}."
                )

            requirement = requirements[0]

            if int(requirement.lessons_per_week or 0) != 5:
                raise CommandError(
                    f"{group.code}: FRE must be 5 lessons/week; "
                    f"found {requirement.lessons_per_week}."
                )

            targets.append(requirement)

            self.stdout.write(
                f"FOUND - {group.code} | "
                f"FRE | "
                f"{requirement.lessons_per_week}/week | "
                f"active={requirement.is_active}"
            )

        with transaction.atomic():
            for requirement in targets:
                requirement.is_active = True
                requirement.save(update_fields=["is_active"])

        self.stdout.write("")
        self.stdout.write("ACTIVATED:")
        for requirement in targets:
            self.stdout.write(
                f"  {requirement.instructional_group.code} | "
                f"FRE | 5 lessons/week | active=True"
            )

        self.stdout.write("")
        self.stdout.write("=" * 76)
        self.stdout.write("GRADE 10 FRE DATABASE REPAIR: COMPLETE")
        self.stdout.write("ONLY THE TWO EXISTING FRE ROWS WERE ACTIVATED.")
        self.stdout.write("NO NEW REQUIREMENTS CREATED.")
        self.stdout.write("NO SOLVER CHANGES MADE.")
        self.stdout.write("=" * 76)
