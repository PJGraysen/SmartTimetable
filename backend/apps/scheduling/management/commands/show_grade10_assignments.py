from django.core.management.base import BaseCommand

from apps.scheduling.models import LessonRequirement, TeacherAssignment


class Command(BaseCommand):
    help = "Show Grade 10 requirements and currently assigned teacher codes."

    def handle(self, *args, **options):
        assignments = (
            TeacherAssignment.objects
            .select_related(
                "teacher",
                "lesson_requirement",
                "lesson_requirement__subject",
                "lesson_requirement__instructional_group",
            )
            .filter(
                lesson_requirement__instructional_group__name="Grade 10",
                lesson_requirement__is_active=True,
            )
        )

        assigned = {
            assignment.lesson_requirement_id: assignment.teacher.employee_code
            for assignment in assignments
        }

        requirements = (
            LessonRequirement.objects
            .select_related("subject", "instructional_group")
            .filter(
                instructional_group__name="Grade 10",
                is_active=True,
            )
            .order_by("subject__name")
        )

        self.stdout.write(
            "\n=== GRADE 10 TEACHER ASSIGNMENT STATUS ===\n"
        )

        for requirement in requirements:
            code = assigned.get(requirement.pk, "NOT ASSIGNED")

            self.stdout.write(
                f"{requirement.subject.name:<45} "
                f"{requirement.lessons_per_week}/week | {code} | "
                f"{requirement.pk}"
            )

        self.stdout.write(
            "\n=== NO DATABASE CHANGES WERE MADE ==="
        )
