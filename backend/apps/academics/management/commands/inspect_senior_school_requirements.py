from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.academics.models import InstructionalGroup, LessonRequirement
from apps.core.models import Term


class Command(BaseCommand):
    help = "Read-only inventory of active Senior School lesson requirements."

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write(" SMARTTIMETABLE PRO - ACTIVE REQUIREMENT INVENTORY")
        self.stdout.write("=" * 72)

        term = (
            Term.objects
            .filter(is_active=True)
            .order_by("-created_at")
            .first()
        )

        if term is None:
            self.stdout.write("ERROR: No active term found.")
            return

        self.stdout.write(f"TERM: {term}")
        self.stdout.write(f"TERM ID: {term.id}")
        self.stdout.write("")

        group_codes = ("10E", "10W", "3E", "3W", "4E", "4W")
        grand_total = 0

        for code in group_codes:
            group = (
                InstructionalGroup.objects
                .filter(
                    code=code,
                    is_active=True,
                )
                .first()
            )

            self.stdout.write("")
            self.stdout.write("-" * 72)

            if group is None:
                self.stdout.write(
                    f"{code}: ACTIVE INSTRUCTIONAL GROUP NOT FOUND"
                )
                continue

            rows = list(
                LessonRequirement.objects
                .filter(
                    term=term,
                    instructional_group=group,
                    is_active=True,
                )
                .select_related("subject")
                .order_by(
                    "requirement_type",
                    "subject__code",
                )
            )

            grand_total += len(rows)

            self.stdout.write(
                f"{code}: {len(rows)} ACTIVE REQUIREMENTS"
            )
            self.stdout.write("-" * 72)

            if not rows:
                self.stdout.write("  NONE")
                continue

            for row in rows:
                self.stdout.write(
                    f"  {row.subject.code:<10} | "
                    f"{row.requirement_type:<10} | "
                    f"{row.lessons_per_week:>2}/week | "
                    f"{row.subject.name}"
                )

        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write(
            f"GRAND TOTAL ACTIVE REQUIREMENTS: {grand_total}"
        )
        self.stdout.write("=" * 72)

        self.stdout.write("")
        self.stdout.write("CONFIRMED LEGACY CODES UNDER REVIEW:")
        self.stdout.write("  COMP")
        self.stdout.write("  HISTGOV")
        self.stdout.write("  LIFE")

        self.stdout.write("")
        self.stdout.write("READ-ONLY INSPECTION COMPLETE")
        self.stdout.write("NO DATABASE CHANGES WERE MADE")
        self.stdout.write("")
