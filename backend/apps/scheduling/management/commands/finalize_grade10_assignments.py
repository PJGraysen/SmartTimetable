from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.scheduling.models import (
    Teacher,
    LessonRequirement,
    TeacherAssignment,
)


class Command(BaseCommand):
    help = "Finalize authoritative Grade 10E/10W teacher assignments."

    GRADE10_ASSIGNMENTS = {
        "Christian Religious Education": "T007",
        "English": "T015",
        "Essential Mathematics / Core Mathematics": "T004",
        "Kiswahili": "T001",
    }

    GRADE10_GROUPS = (
        "Grade 10E",
        "Grade 10W",
    )

    def handle(self, *args, **options):
        self.stdout.write(
            "\n=== QUEEN OF APOSTLES GRADE 10E / 10W ASSIGNMENT FINALIZATION ==="
        )

        # ------------------------------------------------------------
        # 1. RESOLVE AUTHORITATIVE TEACHERS
        #
        # TeacherAssignment has its own is_active flag.
        # A historical/inactive Teacher row must NOT prevent us from
        # reconciling an existing authoritative assignment.
        # ------------------------------------------------------------
        teachers = {}

        for teacher_code in sorted(set(self.GRADE10_ASSIGNMENTS.values())):
            matches = list(
                Teacher.objects.filter(
                    employee_code=teacher_code
                )
            )

            if not matches:
                raise CommandError(
                    f"ABORTED: Teacher {teacher_code} was not found."
                )

            if len(matches) > 1:
                active_matches = [
                    teacher for teacher in matches
                    if teacher.is_active
                ]

                if len(active_matches) == 1:
                    teacher = active_matches[0]
                else:
                    raise CommandError(
                        f"ABORTED: Multiple Teacher rows found for "
                        f"{teacher_code} and no unique active teacher exists."
                    )
            else:
                teacher = matches[0]

            teachers[teacher_code] = teacher

            self.stdout.write(
                f"FOUND | {teacher_code} | "
                f"teacher_active={teacher.is_active}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "PASS | Teacher-code integrity verified."
            )
        )

        # ------------------------------------------------------------
        # 2. LOAD AUTHORITATIVE GRADE 10E / 10W REQUIREMENTS
        # ------------------------------------------------------------
        requirements = {}

        for group_name in self.GRADE10_GROUPS:
            rows = list(
                LessonRequirement.objects
                .select_related("subject", "instructional_group", "term")
                .filter(
                    instructional_group__name=group_name,
                    is_active=True,
                )
            )

            requirements[group_name] = {
                row.subject.name: row
                for row in rows
            }

            self.stdout.write(
                f"FOUND | {group_name} | "
                f"{len(rows)} active requirements"
            )

        # ------------------------------------------------------------
        # 3. VERIFY AUTHORITATIVE REQUIREMENTS
        # ------------------------------------------------------------
        for group_name in self.GRADE10_GROUPS:
            for subject_name in self.GRADE10_ASSIGNMENTS:
                if subject_name not in requirements[group_name]:
                    raise CommandError(
                        f"ABORTED: {group_name} requirement not found: "
                        f"{subject_name}"
                    )

        # ------------------------------------------------------------
        # 4. RECONCILE ASSIGNMENTS
        #
        # For every authoritative subject/group:
        #
        #   expected teacher assignment -> ACTIVE
        #   wrong teacher assignments    -> INACTIVE
        #
        # Historical rows are preserved.
        # A missing expected row is created.
        # ------------------------------------------------------------
        activated = 0
        deactivated = 0
        created = 0
        already_correct = 0

        with transaction.atomic():
            for group_name in self.GRADE10_GROUPS:
                for subject_name, teacher_code in self.GRADE10_ASSIGNMENTS.items():

                    requirement = requirements[group_name][subject_name]
                    teacher = teachers[teacher_code]

                    assignments = list(
                        TeacherAssignment.objects
                        .select_related("teacher")
                        .filter(
                            lesson_requirement=requirement
                        )
                    )

                    expected = [
                        assignment
                        for assignment in assignments
                        if assignment.teacher_id == teacher.id
                    ]

                    # ------------------------------------------------
                    # Deactivate every assignment belonging to the
                    # wrong teacher.
                    # ------------------------------------------------
                    for assignment in assignments:
                        if assignment.teacher_id != teacher.id:
                            if assignment.is_active:
                                assignment.is_active = False
                                assignment.save(
                                    update_fields=[
                                        "is_active",
                                        "updated_at",
                                    ]
                                )

                                deactivated += 1

                                self.stdout.write(
                                    f"DEACTIVATED | {group_name} | "
                                    f"{subject_name} | "
                                    f"{assignment.teacher.employee_code}"
                                )

                    # ------------------------------------------------
                    # Existing authoritative assignment.
                    # ------------------------------------------------
                    if expected:
                        authoritative = expected[0]

                        # If historical duplicate rows exist for the
                        # SAME teacher, keep one active and deactivate
                        # the extras.
                        for duplicate in expected[1:]:
                            if duplicate.is_active:
                                duplicate.is_active = False
                                duplicate.save(
                                    update_fields=[
                                        "is_active",
                                        "updated_at",
                                    ]
                                )

                                deactivated += 1

                                self.stdout.write(
                                    f"DEACTIVATED DUPLICATE | "
                                    f"{group_name} | {subject_name} | "
                                    f"{teacher_code}"
                                )

                        if not authoritative.is_active:
                            authoritative.is_active = True
                            authoritative.save(
                                update_fields=[
                                    "is_active",
                                    "updated_at",
                                ]
                            )

                            activated += 1

                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"ACTIVATED | {group_name} | "
                                    f"{subject_name} | {teacher_code}"
                                )
                            )
                        else:
                            already_correct += 1

                            self.stdout.write(
                                f"ALREADY CORRECT | {group_name} | "
                                f"{subject_name} | {teacher_code}"
                            )

                    # ------------------------------------------------
                    # No historical assignment exists.
                    # ------------------------------------------------
                    else:
                        TeacherAssignment.objects.create(
                            teacher=teacher,
                            lesson_requirement=requirement,
                            is_active=True,
                        )

                        created += 1

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"CREATED | {group_name} | "
                                f"{subject_name} | {teacher_code}"
                            )
                        )

        # ------------------------------------------------------------
        # 5. FINAL REPORT
        # ------------------------------------------------------------
        self.stdout.write(
            "\n=== GRADE 10E / 10W ASSIGNMENT FINALIZATION COMPLETE ==="
        )

        self.stdout.write(
            f"Already correct : {already_correct}"
        )
        self.stdout.write(
            f"Activated       : {activated}"
        )
        self.stdout.write(
            f"Deactivated     : {deactivated}"
        )
        self.stdout.write(
            f"Created         : {created}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\nPASS | Authoritative Grade 10E/10W assignments reconciled."
            )
        )

        self.stdout.write(
            "Teacher employee codes were NOT changed."
        )
        self.stdout.write(
            "FRE and GST requirements were NOT modified."
        )
        self.stdout.write(
            "No solver code was modified."
        )
