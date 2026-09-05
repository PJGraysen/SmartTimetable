from django.core.management.base import BaseCommand
from apps.academics.models import InstructionalGroup, LessonRequirement
from apps.core.models import Term


class Command(BaseCommand):
    help = "Read-only authoritative audit of Grade 10E/10W teacher assignments."

    GROUP_CODES = ("10E", "10W")

    def handle(self, *args, **options):
        term = (
            Term.objects
            .filter(is_active=True)
            .order_by("-start_date", "-created_at")
            .first()
        )

        if term is None:
            self.stdout.write(
                self.style.ERROR("No active academic term exists.")
            )
            return

        groups = list(
            InstructionalGroup.objects
            .filter(
                code__in=self.GROUP_CODES,
                is_active=True,
            )
            .order_by("code")
        )

        self.stdout.write("")
        self.stdout.write("=" * 88)
        self.stdout.write(
            "SMARTTIMETABLE PRO - GRADE 10 TEACHER ASSIGNMENT AUDIT"
        )
        self.stdout.write("=" * 88)
        self.stdout.write("")
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES WILL BE MADE.")
        self.stdout.write("")
        self.stdout.write(f"TERM: {term.name} [{term.id}]")
        self.stdout.write("")

        missing = []
        multiple = []
        inactive_teacher_assignments = []

        for group in groups:
            self.stdout.write("")
            self.stdout.write("-" * 88)
            self.stdout.write(
                f"GROUP: {group.code} | {group.name}"
            )
            self.stdout.write("-" * 88)

            requirements = list(
                LessonRequirement.objects
                .filter(
                    term=term,
                    instructional_group=group,
                    is_active=True,
                )
                .select_related("subject")
                .prefetch_related(
                    "teacher_assignments__teacher"
                )
                .order_by("subject__code")
            )

            for requirement in requirements:
                active_assignments = [
                    assignment
                    for assignment in requirement.teacher_assignments.all()
                    if assignment.is_active
                    and assignment.teacher.is_active
                ]

                inactive_assignments = [
                    assignment
                    for assignment in requirement.teacher_assignments.all()
                    if not assignment.is_active
                    or not assignment.teacher.is_active
                ]

                active_codes = [
                    assignment.teacher.employee_code
                    for assignment in active_assignments
                ]

                inactive_codes = [
                    assignment.teacher.employee_code
                    for assignment in inactive_assignments
                ]

                code = requirement.subject.code
                name = requirement.subject.name
                weekly = requirement.lessons_per_week

                if not active_assignments:
                    status = "MISSING"
                    missing.append((group.code, code))
                elif len(active_assignments) > 1:
                    status = "MULTIPLE"
                    multiple.append(
                        (
                            group.code,
                            code,
                            active_codes,
                        )
                    )
                else:
                    status = "OK"

                self.stdout.write(
                    f"{status:<9} "
                    f"{code:<7} "
                    f"{name:<43} "
                    f"{weekly:>2}/week | "
                    f"ACTIVE={','.join(active_codes) or 'NONE'}"
                )

                if inactive_codes:
                    inactive_teacher_assignments.append(
                        (
                            group.code,
                            code,
                            inactive_codes,
                        )
                    )

        self.stdout.write("")
        self.stdout.write("=" * 88)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 88)

        self.stdout.write(
            f"Missing active teacher assignments : {len(missing)}"
        )
        self.stdout.write(
            f"Multiple active teacher assignments: {len(multiple)}"
        )
        self.stdout.write(
            f"Requirements with inactive/stale assignments: "
            f"{len(inactive_teacher_assignments)}"
        )

        if missing:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "MISSING TEACHERS:"
                )
            )
            for group_code, subject_code in missing:
                self.stdout.write(
                    f"  {group_code}: {subject_code}"
                )

        if multiple:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "MULTIPLE ACTIVE TEACHERS:"
                )
            )
            for group_code, subject_code, teachers in multiple:
                self.stdout.write(
                    f"  {group_code}: {subject_code} -> "
                    f"{', '.join(teachers)}"
                )

        if inactive_teacher_assignments:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "INACTIVE / STALE ASSIGNMENTS:"
                )
            )
            for group_code, subject_code, teachers in inactive_teacher_assignments:
                self.stdout.write(
                    f"  {group_code}: {subject_code} -> "
                    f"{', '.join(teachers)}"
                )

        self.stdout.write("")
        self.stdout.write("=" * 88)

        if not missing and not multiple:
            self.stdout.write(
                self.style.SUCCESS(
                    "PASS: every active Grade 10 requirement has exactly "
                    "one active teacher."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "TEACHER ASSIGNMENT CONFIGURATION REQUIRES REVIEW."
                )
            )

        self.stdout.write("=" * 88)
