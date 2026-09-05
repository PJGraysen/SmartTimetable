from django.core.management.base import BaseCommand
from apps.scheduling.models import Teacher, TeacherAssignment


class Command(BaseCommand):
    help = "Read-only forensic search for the Grade 10 FRE teacher across all assignments."

    def handle(self, *args, **options):
        self.stdout.write("=" * 100)
        self.stdout.write("SMARTTIMETABLE PRO - FULL FRE TEACHER FORENSIC")
        self.stdout.write("=" * 100)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        # Teachers currently without an active Grade 10 teaching assignment
        candidate_codes = [
            "T002", "T003", "T008", "T012",
            "T013", "T017", "T020"
        ]

        teachers = {
            t.employee_code: t
            for t in Teacher.objects.filter(
                employee_code__in=candidate_codes
            ).order_by("employee_code")
        }

        self.stdout.write("=== CANDIDATE TEACHERS ===")
        for code in candidate_codes:
            teacher = teachers.get(code)

            if not teacher:
                self.stdout.write(
                    f"MISSING TEACHER RECORD | {code}"
                )
                continue

            self.stdout.write(
                f"{code} | "
                f"{teacher.first_name} {teacher.last_name} | "
                f"active={teacher.is_active}"
            )

        self.stdout.write("")
        self.stdout.write("=== ALL HISTORICAL ASSIGNMENTS ===")
        self.stdout.write("")

        found_any = False

        for code in candidate_codes:
            teacher = teachers.get(code)

            if not teacher:
                continue

            assignments = (
                TeacherAssignment.objects
                .select_related(
                    "lesson_requirement",
                    "lesson_requirement__subject",
                    "lesson_requirement__instructional_group",
                )
                .filter(teacher=teacher)
                .order_by(
                    "lesson_requirement__subject__code",
                    "lesson_requirement__instructional_group__name",
                )
            )

            self.stdout.write(
                f"--- {code} | "
                f"{teacher.first_name} {teacher.last_name} ---"
            )

            if not assignments:
                self.stdout.write("  NO ASSIGNMENTS EVER FOUND")
                self.stdout.write("")
                continue

            found_any = True

            for assignment in assignments:
                req = assignment.lesson_requirement
                subject = req.subject
                group = req.instructional_group

                self.stdout.write(
                    f"  {subject.code:<8} | "
                    f"{subject.name:<45} | "
                    f"{group.name:<25} | "
                    f"REQ_ACTIVE={req.is_active} | "
                    f"ASSIGN_ACTIVE={assignment.is_active} | "
                    f"{req.lessons_per_week}/week"
                )

            self.stdout.write("")

        self.stdout.write("=" * 100)
        self.stdout.write("=== ALL FRENCH REQUIREMENTS IN DATABASE ===")
        self.stdout.write("=" * 100)

        fre_assignments = (
            TeacherAssignment.objects
            .select_related(
                "teacher",
                "lesson_requirement",
                "lesson_requirement__subject",
                "lesson_requirement__instructional_group",
            )
            .filter(lesson_requirement__subject__code="FRE")
            .order_by(
                "lesson_requirement__instructional_group__name",
                "teacher__employee_code",
            )
        )

        if not fre_assignments.exists():
            self.stdout.write("NO FRE TEACHER ASSIGNMENTS EXIST ANYWHERE.")
        else:
            for assignment in fre_assignments:
                req = assignment.lesson_requirement
                self.stdout.write(
                    f"{req.instructional_group.name} | "
                    f"teacher={assignment.teacher.employee_code} | "
                    f"{assignment.teacher.first_name} {assignment.teacher.last_name} | "
                    f"REQ_ACTIVE={req.is_active} | "
                    f"ASSIGN_ACTIVE={assignment.is_active}"
                )

        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write("FORENSIC COMPLETE")
        self.stdout.write("NO DATABASE CHANGES")
        self.stdout.write("=" * 100)
