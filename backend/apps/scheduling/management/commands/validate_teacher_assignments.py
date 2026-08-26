from django.core.management.base import BaseCommand

from apps.scheduling.models import (
    LessonRequirement,
    Teacher,
    TeacherAssignment,
)


class Command(BaseCommand):
    help = (
        "Validate teacher assignments for active Grade 10 lesson requirements "
        "without modifying the database."
    )

    def handle(self, *args, **options):
        errors = []

        self.stdout.write(
            "\n=== SMART TIMETABLE TEACHER ASSIGNMENT VALIDATION ===\n"
        )

        # ------------------------------------------------------------
        # 1. Teacher-code integrity
        # ------------------------------------------------------------
        teachers = list(
            Teacher.objects.all().order_by("teacher_number")
        )

        expected_codes = {
            f"T{number:03d}"
            for number in range(1, 21)
        }

        actual_codes = {
            teacher.employee_code
            for teacher in teachers
        }

        if actual_codes != expected_codes:
            errors.append(
                "Teacher codes do not exactly match T001-T020."
            )

        for teacher in teachers:
            expected_code = f"T{teacher.teacher_number:03d}"

            if teacher.employee_code != expected_code:
                errors.append(
                    f"Teacher {teacher.pk}: "
                    f"teacher_number={teacher.teacher_number} "
                    f"but employee_code={teacher.employee_code}; "
                    f"expected {expected_code}."
                )

        if not errors:
            self.stdout.write(
                self.style.SUCCESS(
                    "PASS | Teacher codes T001-T020 are intact."
                )
            )

        # ------------------------------------------------------------
        # 2. Active Grade 10 requirements
        # ------------------------------------------------------------
        requirements = list(
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

        self.stdout.write(
            f"Active Grade 10 requirements: {len(requirements)}"
        )

        # ------------------------------------------------------------
        # 3. Assignment counts
        # ------------------------------------------------------------
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
                self.stdout.write(
                    self.style.WARNING(
                        f"MISSING | {subject} | "
                        f"{requirement.lessons_per_week}/week"
                    )
                )
                errors.append(
                    f"Missing teacher assignment: {subject}"
                )

            elif len(assignments) > 1:
                codes = ", ".join(
                    sorted(
                        assignment.teacher.employee_code
                        for assignment in assignments
                    )
                )

                self.stdout.write(
                    self.style.ERROR(
                        f"DUPLICATE | {subject} | {codes}"
                    )
                )

                errors.append(
                    f"Multiple teacher assignments: "
                    f"{subject} -> {codes}"
                )

            else:
                assignment = assignments[0]
                code = assignment.teacher.employee_code

                self.stdout.write(
                    self.style.SUCCESS(
                        f"ASSIGNED | {code} | {subject} | "
                        f"{requirement.lessons_per_week}/week"
                    )
                )

        # ------------------------------------------------------------
        # 4. Detect assignments pointing at inactive requirements
        # ------------------------------------------------------------
        stale_count = (
            TeacherAssignment.objects
            .filter(
                lesson_requirement__is_active=False
            )
            .count()
        )

        if stale_count:
            self.stdout.write(
                self.style.ERROR(
                    f"STALE | {stale_count} assignment(s) "
                    f"point to inactive requirements."
                )
            )

            errors.append(
                f"{stale_count} stale TeacherAssignment row(s)."
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "PASS | No assignments point to inactive requirements."
                )
            )

        # ------------------------------------------------------------
        # 5. Final result
        # ------------------------------------------------------------
        self.stdout.write("\n=== VALIDATION RESULT ===")

        if errors:
            self.stdout.write(
                self.style.WARNING(
                    f"VALIDATION INCOMPLETE | {len(errors)} issue(s)"
                )
            )

            self.stdout.write(
                "\nThe database was NOT modified."
            )

            self.stdout.write(
                "\nMissing assignments are intentionally not guessed."
            )

            return

        self.stdout.write(
            self.style.SUCCESS(
                "VALID | All active Grade 10 requirements have exactly "
                "one teacher assignment."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Teacher codes remain immutable."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "No database changes were made."
            )
        )
