from django.core.management.base import BaseCommand, CommandError

from apps.scheduling.models import (
    LessonRequirement,
    TeacherAssignment,
)


class Command(BaseCommand):
    help = (
        "Verify that every active Grade 10 lesson requirement has exactly "
        "one teacher assignment."
    )

    def handle(self, *args, **options):
        requirements = (
            LessonRequirement.objects
            .select_related(
                "subject",
                "instructional_group",
            )
            .filter(
                instructional_group__name="Grade 10",
                is_active=True,
            )
            .order_by("subject__name")
        )

        failures = []

        for requirement in requirements:
            assignments = list(
                TeacherAssignment.objects
                .select_related("teacher")
                .filter(
                    lesson_requirement=requirement
                )
            )

            subject = requirement.subject.name

            if len(assignments) == 0:
                failures.append(
                    f"{subject}: NO TEACHER ASSIGNED"
                )

            elif len(assignments) > 1:
                codes = ", ".join(
                    sorted(
                        assignment.teacher.employee_code
                        for assignment in assignments
                    )
                )

                failures.append(
                    f"{subject}: MULTIPLE TEACHERS [{codes}]"
                )

            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK | {subject} | "
                        f"{assignments[0].teacher.employee_code}"
                    )
                )

        self.stdout.write("\n=== TEACHER ASSIGNMENT GATE ===")

        if failures:
            self.stdout.write(
                self.style.ERROR(
                    f"BLOCKED | {len(failures)} requirement(s) "
                    "cannot enter the scheduling engine."
                )
            )

            for failure in failures:
                self.stdout.write(
                    self.style.ERROR(
                        f"  {failure}"
                    )
                )

            raise CommandError(
                "Teacher assignment validation failed. "
                "Scheduling generation must not proceed."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nPASSED | Every active Grade 10 requirement "
                "has exactly one teacher."
            )
        )
