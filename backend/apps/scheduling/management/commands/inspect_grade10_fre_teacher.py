from django.core.management.base import BaseCommand
from apps.scheduling.models import Teacher, TeacherAssignment, LessonRequirement


class Command(BaseCommand):
    help = "Read-only forensic inspection of Grade 10 French teacher assignments."

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("SMARTTIMETABLE PRO - GRADE 10 FRE TEACHER FORENSIC")
        self.stdout.write("=" * 80)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        requirements = list(
            LessonRequirement.objects
            .select_related("subject", "instructional_group")
            .filter(subject__code="FRE")
            .order_by("instructional_group__name")
        )

        if not requirements:
            self.stdout.write(self.style.ERROR(
                "FAIL - No FRE lesson requirements found."
            ))
            return

        self.stdout.write("=== FRE REQUIREMENTS ===")
        for req in requirements:
            self.stdout.write(
                f"GROUP={req.instructional_group.name} | "
                f"REQ_ID={req.id} | "
                f"ACTIVE={req.is_active} | "
                f"LESSONS={req.lessons_per_week}/week"
            )

        self.stdout.write("")
        self.stdout.write("=== ALL FRE TEACHER ASSIGNMENTS ===")

        assignment_rows = []

        for req in requirements:
            assignments = list(
                TeacherAssignment.objects
                .select_related("teacher", "lesson_requirement")
                .filter(lesson_requirement=req)
                .order_by("teacher__employee_code")
            )

            if not assignments:
                self.stdout.write(
                    f"{req.instructional_group.name} | FRE | NO ASSIGNMENTS"
                )
                continue

            for assignment in assignments:
                teacher = assignment.teacher
                assignment_rows.append(assignment)

                self.stdout.write(
                    f"{req.instructional_group.name} | FRE | "
                    f"teacher={teacher.employee_code} | "
                    f"teacher_active={teacher.is_active} | "
                    f"assignment_active={assignment.is_active} | "
                    f"assignment_id={assignment.id}"
                )

        self.stdout.write("")
        self.stdout.write("=== TEACHERS EVER ASSOCIATED WITH FRE ===")

        teacher_ids = sorted({
            assignment.teacher_id
            for assignment in assignment_rows
        })

        if not teacher_ids:
            self.stdout.write("NONE")
        else:
            teachers = (
                Teacher.objects
                .filter(id__in=teacher_ids)
                .order_by("employee_code")
            )

            for teacher in teachers:
                self.stdout.write(
                    f"{teacher.employee_code} | "
                    f"active={teacher.is_active} | "
                    f"id={teacher.id}"
                )

        self.stdout.write("")
        self.stdout.write("=== ACTIVE TEACHERS NOT CURRENTLY ASSIGNED TO FRE ===")

        assigned_active_teacher_ids = {
            assignment.teacher_id
            for assignment in assignment_rows
            if assignment.is_active and assignment.teacher.is_active
        }

        available = (
            Teacher.objects
            .filter(is_active=True)
            .exclude(id__in=assigned_active_teacher_ids)
            .order_by("employee_code")
        )

        for teacher in available:
            self.stdout.write(
                f"AVAILABLE | {teacher.employee_code} | "
                f"active={teacher.is_active}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write("FRE TEACHER FORENSIC COMPLETE")
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("=" * 80)
