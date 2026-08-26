from django.core.management.base import BaseCommand
from django.db import transaction

from apps.scheduling.models import (
    Teacher,
    LessonRequirement,
    TeacherAssignment,
)


class Command(BaseCommand):
    help = (
        "Safely populate unambiguous timetable teacher assignments. "
        "Teacher codes are immutable and existing assignments are preserved."
    )

    # IMPORTANT:
    # These are teacher codes already present in the database.
    # They are NOT being created, changed, or renumbered here.
    UNAMBIGUOUS_ASSIGNMENTS = {
        "Physical Education": "T014",
        "ICT Skills": "T014",
        "Community Service Learning": "T016",
    }

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "\n=== SMART TIMETABLE TEACHER ASSIGNMENT SAFETY CHECK ==="
            )
        )

        # ------------------------------------------------------------
        # 1. Verify the immutable teacher-code system.
        # ------------------------------------------------------------
        teachers = {
            teacher.employee_code: teacher
            for teacher in Teacher.objects.all()
        }

        expected_codes = {
            f"T{number:03d}"
            for number in range(1, 21)
        }

        actual_codes = set(teachers.keys())

        if actual_codes != expected_codes:
            self.stdout.write(
                self.style.ERROR(
                    "ABORTED: Existing teacher codes do not exactly match "
                    "the expected T001-T020 set."
                )
            )

            self.stdout.write(
                f"Expected: {sorted(expected_codes)}"
            )
            self.stdout.write(
                f"Actual:   {sorted(actual_codes)}"
            )

            return

        for code, teacher in teachers.items():
            expected_number = int(code[1:])

            if teacher.teacher_number != expected_number:
                self.stdout.write(
                    self.style.ERROR(
                        f"ABORTED: {code} has teacher_number="
                        f"{teacher.teacher_number}, expected "
                        f"{expected_number}."
                    )
                )
                return

        self.stdout.write(
            self.style.SUCCESS(
                "Teacher-code integrity verified: T001-T020."
            )
        )

        # ------------------------------------------------------------
        # 2. Show existing assignments.
        # ------------------------------------------------------------
        existing = set(
            TeacherAssignment.objects.values_list(
                "teacher_id",
                "lesson_requirement_id",
            )
        )

        self.stdout.write(
            f"Existing TeacherAssignment rows: {len(existing)}"
        )

        # ------------------------------------------------------------
        # 3. Process only active lesson requirements.
        # ------------------------------------------------------------
        requirements = (
            LessonRequirement.objects
            .select_related("subject", "instructional_group", "term")
            .filter(is_active=True)
            .order_by("instructional_group__name", "subject__name")
        )

        created = 0
        already_present = 0
        unresolved = []

        with transaction.atomic():

            for requirement in requirements:

                subject_name = requirement.subject.name.strip()

                teacher_code = self.UNAMBIGUOUS_ASSIGNMENTS.get(
                    subject_name
                )

                # ----------------------------------------------------
                # Do NOT guess ambiguous subjects.
                # ----------------------------------------------------
                if teacher_code is None:
                    unresolved.append(
                        (
                            requirement,
                            subject_name,
                        )
                    )
                    continue

                teacher = teachers.get(teacher_code)

                if teacher is None:
                    raise RuntimeError(
                        f"Teacher {teacher_code} does not exist."
                    )

                pair = (
                    teacher.pk,
                    requirement.pk,
                )

                if pair in existing:
                    already_present += 1

                    self.stdout.write(
                        f"EXISTS | {teacher_code} | "
                        f"{requirement.instructional_group.name} | "
                        f"{subject_name}"
                    )
                    continue

                TeacherAssignment.objects.create(
                    teacher=teacher,
                    lesson_requirement=requirement,
                )

                existing.add(pair)
                created += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"CREATED | {teacher_code} | "
                        f"{requirement.instructional_group.name} | "
                        f"{subject_name}"
                    )
                )

        # ------------------------------------------------------------
        # 4. Report unresolved assignments.
        # ------------------------------------------------------------
        self.stdout.write("\n=== AMBIGUOUS SUBJECTS NOT AUTO-ASSIGNED ===")

        for requirement, subject_name in unresolved:
            self.stdout.write(
                f"UNRESOLVED | "
                f"{requirement.instructional_group.name} | "
                f"{subject_name} | "
                f"{requirement.lessons_per_week}/week"
            )

        # ------------------------------------------------------------
        # 5. Final report.
        # ------------------------------------------------------------
        self.stdout.write("\n=== RESULT ===")

        self.stdout.write(
            self.style.SUCCESS(
                f"Created assignments: {created}"
            )
        )

        self.stdout.write(
            f"Already present: {already_present}"
        )

        self.stdout.write(
            f"Ambiguous/unresolved: {len(unresolved)}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\nTeacher codes were NOT changed."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "No existing TeacherAssignment rows were deleted."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Assignment population completed safely."
            )
        )
