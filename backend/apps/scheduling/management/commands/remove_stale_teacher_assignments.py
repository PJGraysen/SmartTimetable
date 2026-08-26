from django.core.management.base import BaseCommand
from django.db import transaction

from apps.scheduling.models import TeacherAssignment


class Command(BaseCommand):
    help = "Remove only stale TeacherAssignments attached to inactive LessonRequirements."

    def handle(self, *args, **options):
        stale = list(
            TeacherAssignment.objects
            .select_related(
                "teacher",
                "lesson_requirement",
                "lesson_requirement__subject",
                "lesson_requirement__instructional_group",
            )
            .filter(lesson_requirement__is_active=False)
        )

        if not stale:
            self.stdout.write(
                self.style.SUCCESS(
                    "No stale assignments found."
                )
            )
            return

        self.stdout.write("\n=== STALE ASSIGNMENTS ===")

        for assignment in stale:
            self.stdout.write(
                f"{assignment.teacher.employee_code} | "
                f"{assignment.lesson_requirement.subject.name} | "
                f"{assignment.lesson_requirement.instructional_group.name}"
            )

        with transaction.atomic():
            count = len(stale)

            for assignment in stale:
                assignment.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nRemoved {count} stale assignment(s)."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Teacher records and teacher codes were NOT changed."
            )
        )
