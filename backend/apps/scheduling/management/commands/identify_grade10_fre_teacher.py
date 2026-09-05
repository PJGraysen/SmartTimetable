from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.scheduling.models import Teacher, TeacherAssignment


class Command(BaseCommand):
    help = "Read-only inspection of teacher subject assignments to identify Grade 10 FRE teacher."

    def handle(self, *args, **options):
        self.stdout.write("=" * 90)
        self.stdout.write("SMARTTIMETABLE PRO - IDENTIFY GRADE 10 FRE TEACHER")
        self.stdout.write("=" * 90)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        teachers = Teacher.objects.filter(is_active=True).order_by("employee_code")

        self.stdout.write("=== ACTIVE TEACHERS AND CURRENT SUBJECT LOADS ===")
        self.stdout.write("")

        for teacher in teachers:
            assignments = (
                TeacherAssignment.objects
                .select_related(
                    "lesson_requirement",
                    "lesson_requirement__subject",
                    "lesson_requirement__instructional_group",
                )
                .filter(
                    teacher=teacher,
                    is_active=True,
                    lesson_requirement__is_active=True,
                )
                .order_by(
                    "lesson_requirement__subject__code",
                    "lesson_requirement__instructional_group__name",
                )
            )

            subjects = {}

            for assignment in assignments:
                subject = assignment.lesson_requirement.subject
                group = assignment.lesson_requirement.instructional_group

                code = subject.code
                name = subject.name
                group_name = group.name

                subjects.setdefault(code, {
                    "name": name,
                    "groups": set(),
                    "lessons": 0,
                })

                subjects[code]["groups"].add(group_name)
                subjects[code]["lessons"] += (
                    assignment.lesson_requirement.lessons_per_week
                )

            if subjects:
                self.stdout.write(
                    f"{teacher.employee_code} | {getattr(teacher, 'name', '')}"
                )

                for code in sorted(subjects):
                    data = subjects[code]
                    groups = ", ".join(sorted(data["groups"]))

                    self.stdout.write(
                        f"  {code:<8} | "
                        f"{data['name']:<45} | "
                        f"{data['lessons']:>2}/week | "
                        f"{groups}"
                    )
            else:
                self.stdout.write(
                    f"{teacher.employee_code} | {getattr(teacher, 'name', '')} | NO ACTIVE ASSIGNMENTS"
                )

            self.stdout.write("")

        self.stdout.write("=" * 90)
        self.stdout.write("=== TEACHER MODEL FIELDS ===")
        self.stdout.write("=" * 90)

        for field in Teacher._meta.fields:
            self.stdout.write(
                f"{field.name} | type={field.__class__.__name__}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 90)
        self.stdout.write("IDENTIFICATION INSPECTION COMPLETE")
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("=" * 90)
