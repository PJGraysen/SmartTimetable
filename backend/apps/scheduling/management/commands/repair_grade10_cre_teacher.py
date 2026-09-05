from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.scheduling.models import (
    Teacher,
    LessonRequirement,
    TeacherAssignment,
)


class Command(BaseCommand):
    help = "Repair authoritative Grade 10 CRE teacher assignment for 10E/10W."

    TEACHER_CODE = "T007"
    SUBJECT_NAME = "Christian Religious Education"
    GROUPS = ("Grade 10E", "Grade 10W")

    def handle(self, *args, **options):
        self.stdout.write(
            "\n" + "=" * 78
        )
        self.stdout.write(
            "SMARTTIMETABLE PRO - GRADE 10 CRE TEACHER REPAIR"
        )
        self.stdout.write(
            "=" * 78
        )

        teacher = (
            Teacher.objects
            .filter(employee_code=self.TEACHER_CODE)
            .first()
        )

        if teacher is None:
            raise CommandError(
                f"ABORTED: Teacher {self.TEACHER_CODE} does not exist."
            )

        self.stdout.write(
            f"TEACHER: {self.TEACHER_CODE} | "
            f"id={teacher.id} | "
            f"active_before={teacher.is_active}"
        )

        with transaction.atomic():

            # --------------------------------------------------------
            # 1. The authoritative Grade 10 CRE teacher must be active.
            # --------------------------------------------------------
            if not teacher.is_active:
                Teacher.objects.filter(
                    pk=teacher.pk
                ).update(
                    is_active=True
                )

                teacher.refresh_from_db()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"ACTIVATED TEACHER | {self.TEACHER_CODE}"
                    )
                )
            else:
                self.stdout.write(
                    f"ALREADY ACTIVE | {self.TEACHER_CODE}"
                )

            # --------------------------------------------------------
            # 2. Reconcile CRE for both authoritative groups.
            # --------------------------------------------------------
            for group_name in self.GROUPS:

                requirement = (
                    LessonRequirement.objects
                    .select_related("subject", "instructional_group")
                    .filter(
                        instructional_group__name=group_name,
                        subject__name=self.SUBJECT_NAME,
                        is_active=True,
                    )
                    .first()
                )

                if requirement is None:
                    raise CommandError(
                        f"ABORTED: Active CRE requirement not found "
                        f"for {group_name}."
                    )

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

                # Deactivate all non-authoritative assignments.
                wrong_ids = [
                    assignment.id
                    for assignment in assignments
                    if assignment.teacher_id != teacher.id
                    and assignment.is_active
                ]

                if wrong_ids:
                    changed = (
                        TeacherAssignment.objects
                        .filter(id__in=wrong_ids)
                        .update(is_active=False)
                    )

                    self.stdout.write(
                        f"DEACTIVATED | {group_name} | "
                        f"{changed} stale assignment(s)"
                    )

                # Existing authoritative assignment.
                if expected:
                    authoritative = expected[0]

                    # Direct queryset update deliberately bypasses
                    # model save/signal behavior.
                    TeacherAssignment.objects.filter(
                        pk=authoritative.pk
                    ).update(
                        is_active=True
                    )

                    # Historical duplicate rows for the same teacher:
                    # retain exactly one active assignment.
                    duplicate_ids = [
                        assignment.id
                        for assignment in expected[1:]
                    ]

                    if duplicate_ids:
                        TeacherAssignment.objects.filter(
                            id__in=duplicate_ids
                        ).update(
                            is_active=False
                        )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"ACTIVE | {group_name} | "
                            f"CRE -> {self.TEACHER_CODE}"
                        )
                    )

                # No authoritative assignment exists: create one.
                else:
                    TeacherAssignment.objects.create(
                        teacher=teacher,
                        lesson_requirement=requirement,
                        is_active=True,
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"CREATED | {group_name} | "
                            f"CRE -> {self.TEACHER_CODE}"
                        )
                    )

        # ------------------------------------------------------------
        # 3. Verify actual persisted state.
        # ------------------------------------------------------------
        teacher.refresh_from_db()

        self.stdout.write("\n=== PERSISTENCE VERIFICATION ===")
        self.stdout.write(
            f"T007 teacher active: {teacher.is_active}"
        )

        for group_name in self.GROUPS:
            requirement = (
                LessonRequirement.objects
                .filter(
                    instructional_group__name=group_name,
                    subject__name=self.SUBJECT_NAME,
                    is_active=True,
                )
                .first()
            )

            active_assignments = list(
                TeacherAssignment.objects
                .select_related("teacher")
                .filter(
                    lesson_requirement=requirement,
                    is_active=True,
                )
            )

            codes = [
                assignment.teacher.employee_code
                for assignment in active_assignments
            ]

            self.stdout.write(
                f"{group_name} CRE ACTIVE TEACHERS: "
                f"{', '.join(codes) if codes else 'NONE'}"
            )

            if codes != [self.TEACHER_CODE]:
                raise CommandError(
                    f"VERIFICATION FAILED: {group_name} CRE "
                    f"expected only {self.TEACHER_CODE}, got {codes}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "\nPASS | Grade 10E/10W CRE now has exactly T007 active."
            )
        )
        self.stdout.write("=" * 78)
