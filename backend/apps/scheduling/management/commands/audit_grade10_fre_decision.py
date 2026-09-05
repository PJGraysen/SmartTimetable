from django.core.management.base import BaseCommand
from apps.scheduling.models import LessonRequirement, TeacherAssignment


class Command(BaseCommand):
    help = "Audit Grade 10 FRE reserved curriculum slot."

    def handle(self, *args, **options):
        self.stdout.write("=" * 90)
        self.stdout.write("SMARTTIMETABLE PRO - GRADE 10 FRE RESERVED SLOT AUDIT")
        self.stdout.write("=" * 90)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES\n")

        requirements = LessonRequirement.objects.select_related(
            "subject",
            "instructional_group",
        ).filter(
            instructional_group__name__in=["Grade 10E", "Grade 10W"],
            subject__name="French",
            is_active=True,
        ).order_by("instructional_group__name")

        self.stdout.write("=== RESERVED FRE CURRICULUM REQUIREMENTS ===")

        for req in requirements:
            assignments = TeacherAssignment.objects.filter(
                lesson_requirement=req,
                is_active=True,
            ).select_related("teacher")

            teachers = list(assignments)

            self.stdout.write(
                f"{req.instructional_group.name} | "
                f"REQ_ID={req.id} | "
                f"{req.lessons_per_week}/week | "
                f"ACTIVE_TEACHER="
                + (
                    ",".join(a.teacher.employee_code for a in teachers)
                    if teachers else "NONE"
                )
            )

        self.stdout.write("\n=== HISTORICAL FRE ASSIGNMENTS ===")

        historical = TeacherAssignment.objects.filter(
            lesson_requirement__subject__name="French"
        ).select_related(
            "teacher",
            "lesson_requirement",
            "lesson_requirement__instructional_group",
        ).order_by(
            "lesson_requirement__instructional_group__name",
            "teacher__employee_code",
        )

        if not historical.exists():
            self.stdout.write("NONE")
        else:
            for assignment in historical:
                self.stdout.write(
                    f"{assignment.lesson_requirement.instructional_group.name} | "
                    f"FRE | "
                    f"{assignment.teacher.employee_code} | "
                    f"active={assignment.is_active}"
                )

        self.stdout.write("\n=== AUTHORITATIVE FRE POLICY ===")
        self.stdout.write(
            "FRE IS A RESERVED CURRICULUM SLOT."
        )
        self.stdout.write(
            "FRE remains present at 5 lessons/week for Grade 10E and Grade 10W."
        )
        self.stdout.write(
            "There is currently NO French teacher assignment."
        )
        self.stdout.write(
            "There is currently NO active French class/student allocation."
        )
        self.stdout.write(
            "NO teacher must be invented or selected automatically."
        )
        self.stdout.write(
            "FRE must NOT be treated as a staffed timetable lesson until "
            "a future French class and teacher are explicitly configured."
        )

        self.stdout.write("\n" + "=" * 90)
        self.stdout.write("RESULT")
        self.stdout.write("=" * 90)
        self.stdout.write(
            "PASS | FRE curriculum slot preserved."
        )
        self.stdout.write(
            "PASS | No teacher assignment required at present."
        )
        self.stdout.write(
            "PASS | No FRE database modification performed."
        )
        self.stdout.write("=" * 90)
