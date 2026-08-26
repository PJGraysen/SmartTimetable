from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Term
from apps.scheduling.engine.infrastructure.django_loader import (
    load_scheduling_problem,
)


class Command(BaseCommand):
    help = "Inspect the scheduling problem loaded for the current active term."

    def handle(self, *args, **options):
        self.stdout.write(
            "\n=== SCHEDULING PROBLEM LOAD DIAGNOSTIC ===\n"
        )

        terms = list(
            Term.objects
            .order_by("-start_date", "name")
        )

        if not terms:
            raise CommandError("No academic term exists.")

        self.stdout.write("Available terms:")

        for term in terms:
            self.stdout.write(
                f"  {term.pk} | {term.name}"
            )

        # Use the term attached to the active Grade 10 requirements.
        from apps.scheduling.models import LessonRequirement

        requirement = (
            LessonRequirement.objects
            .select_related("term", "instructional_group")
            .filter(
                instructional_group__name="Grade 10",
                is_active=True,
            )
            .order_by("subject__name")
            .first()
        )

        if requirement is None:
            raise CommandError(
                "No active Grade 10 LessonRequirement exists."
            )

        term = requirement.term

        self.stdout.write(
            self.style.SUCCESS(
                f"\nUsing Grade 10 requirement term: "
                f"{term.pk} | {term.name}"
            )
        )

        problem = load_scheduling_problem(term)

        self.stdout.write(
            f"\nProblem type: {type(problem).__name__}"
        )

        # ------------------------------------------------------------
        # Top-level fields
        # ------------------------------------------------------------
        self.stdout.write("\n=== PROBLEM FIELDS ===")

        for name in dir(problem):
            if name.startswith("_"):
                continue

            try:
                value = getattr(problem, name)
            except Exception:
                continue

            if callable(value):
                continue

            if isinstance(value, (str, int, float, bool, type(None))):
                self.stdout.write(
                    f"{name} = {value}"
                )
            elif hasattr(value, "__len__"):
                try:
                    self.stdout.write(
                        f"{name} = {type(value).__name__} "
                        f"(count={len(value)})"
                    )
                except Exception:
                    self.stdout.write(
                        f"{name} = {type(value).__name__}"
                    )
            else:
                self.stdout.write(
                    f"{name} = {type(value).__name__}"
                )

        # ------------------------------------------------------------
        # Known scheduling collections
        # ------------------------------------------------------------
        collections = [
            "instructional_groups",
            "lesson_requirements",
            "periods",
            "rooms",
            "room_availability",
            "teachers",
            "teacher_assignments",
            "teacher_availability",
            "teacher_free_afternoons",
            "slots",
        ]

        for name in collections:
            if not hasattr(problem, name):
                self.stdout.write(
                    f"\n{name}: NOT PRESENT"
                )
                continue

            value = getattr(problem, name)

            try:
                count = len(value)
            except Exception:
                count = "?"

            self.stdout.write(
                f"\n{name}: {type(value).__name__} | count={count}"
            )

            try:
                for item in value:
                    self.stdout.write(
                        f"  {item}"
                    )
            except TypeError:
                pass

        self.stdout.write(
            "\n=== DIAGNOSTIC COMPLETE: NO DATABASE CHANGES ==="
        )
