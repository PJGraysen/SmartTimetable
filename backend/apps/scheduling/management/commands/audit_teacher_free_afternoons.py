from django.core.management.base import BaseCommand

from apps.scheduling.models import Teacher, TeacherFreeAfternoon


class Command(BaseCommand):
    help = "Audit teacher free-afternoon assignments without modifying the database."

    def handle(self, *args, **options):
        self.stdout.write(
            "\n=== TEACHER FREE-AFTERNOON AUDIT ===\n"
        )

        teachers = (
            Teacher.objects
            .all()
            .order_by("teacher_number")
        )

        problems = []

        for teacher in teachers:
            assignments = list(
                TeacherFreeAfternoon.objects
                .filter(
                    teacher=teacher,
                    is_active=True,
                )
            )

            if len(assignments) == 0:
                status = "MISSING"
                problems.append(
                    f"{teacher.employee_code}: 0 active free afternoons"
                )

            elif len(assignments) == 1:
                assignment = assignments[0]
                status = "OK"

                afternoon = getattr(
                    assignment,
                    "afternoon",
                    None,
                )

                if afternoon is None:
                    afternoon = getattr(
                        assignment,
                        "day_of_week",
                        None,
                    )

                self.stdout.write(
                    f"OK      | {teacher.employee_code} | "
                    f"{afternoon}"
                )
                continue

            else:
                status = "DUPLICATE"
                problems.append(
                    f"{teacher.employee_code}: "
                    f"{len(assignments)} active free afternoons"
                )

            self.stdout.write(
                f"{status:<8} | {teacher.employee_code}"
            )

        self.stdout.write(
            "\n=== FREE-AFTERNOON VALIDATION ==="
        )

        if problems:
            self.stdout.write(
                self.style.ERROR(
                    f"BLOCKED | {len(problems)} teacher(s) "
                    "do not have exactly one active free afternoon."
                )
            )

            for problem in problems:
                self.stdout.write(
                    self.style.ERROR(
                        f"  {problem}"
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "PASSED | Every teacher has exactly one "
                    "active free-afternoon assignment."
                )
            )

        self.stdout.write(
            "\n=== NO DATABASE CHANGES WERE MADE ==="
        )
