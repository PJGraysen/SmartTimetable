from django.core.management.base import BaseCommand
from apps.scheduling.models import Teacher, LessonRequirement, TeacherAssignment


class Command(BaseCommand):
    help = "Inspect teacher codes, lesson requirements, instructional groups and assignments without modifying data."

    def handle(self, *args, **options):
        self.stdout.write("\n=== EXISTING TEACHERS ===")

        teachers = Teacher.objects.all().order_by("id")

        for teacher in teachers:
            values = {}

            for field in teacher._meta.fields:
                try:
                    value = getattr(teacher, field.name)

                    if hasattr(value, "pk"):
                        value = f"{value} [pk={value.pk}]"

                    values[field.name] = value
                except Exception:
                    values[field.name] = "<unavailable>"

            self.stdout.write(
                f"Teacher id={teacher.pk} | {values}"
            )

        self.stdout.write("\n=== LESSON REQUIREMENTS ===")

        requirements = LessonRequirement.objects.all().order_by("id")

        for requirement in requirements:
            values = {}

            for field in requirement._meta.fields:
                try:
                    value = getattr(requirement, field.name)

                    if hasattr(value, "pk"):
                        value = f"{value} [pk={value.pk}]"

                    values[field.name] = value
                except Exception:
                    values[field.name] = "<unavailable>"

            self.stdout.write(
                f"LessonRequirement id={requirement.pk} | {values}"
            )

        self.stdout.write("\n=== EXISTING TEACHER ASSIGNMENTS ===")

        assignments = TeacherAssignment.objects.select_related(
            "teacher",
            "lesson_requirement",
        ).order_by("id")

        for assignment in assignments:
            self.stdout.write(
                f"Assignment id={assignment.pk} | "
                f"teacher={assignment.teacher} "
                f"(pk={assignment.teacher_id}) | "
                f"lesson_requirement={assignment.lesson_requirement} "
                f"(pk={assignment.lesson_requirement_id})"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nInspection complete. NO DATABASE CHANGES WERE MADE."
            )
        )
