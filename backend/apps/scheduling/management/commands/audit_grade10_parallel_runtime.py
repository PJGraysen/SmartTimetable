from django.core.management.base import BaseCommand

from apps.academics.models import InstructionalGroup, LessonRequirement

from apps.scheduling.engine.application.grade10_parallel_blocks import (
    describe_grade10_parallel_blocks,
    grade10_parallel_slot_count,
    grade10_parallel_subject_count,
    validate_grade10_parallel_blocks,
)


class Command(BaseCommand):
    help = "Read-only audit of Grade 10 parallel elective runtime configuration."

    def teacher_label(self, teacher):
        for field_name in (
            "code",
            "employee_code",
            "staff_code",
            "employee_number",
            "staff_number",
            "teacher_code",
            "name",
            "full_name",
        ):
            value = getattr(teacher, field_name, None)
            if value not in (None, ""):
                return str(value)

        return str(getattr(teacher, "pk", "UNKNOWN"))

    def subject_label(self, subject):
        if subject is not None:
            for field_name in (
                "code",
                "short_code",
                "abbreviation",
                "name",
                "title",
            ):
                value = getattr(subject, field_name, None)
                if value not in (None, ""):
                    return str(value)

        return "UNKNOWN"

    def requirement_subject_label(self, requirement):
        subject = getattr(requirement, "subject", None)

        if subject is not None:
            return self.subject_label(subject)

        for field_name in (
            "subject_code",
            "subject_name",
            "name",
            "code",
        ):
            value = getattr(requirement, field_name, None)
            if value not in (None, ""):
                return str(value)

        return str(getattr(requirement, "pk", "UNKNOWN"))

    def lesson_count(self, requirement):
        """
        Resolve the weekly lesson count using the actual Django model field.
        The current model uses lessons_per_week.
        """
        for field_name in (
            "lessons_per_week",
            "periods_per_week",
            "weekly_lessons",
            "lessons",
        ):
            value = getattr(requirement, field_name, None)

            if value is not None:
                return value

        return "UNKNOWN"

    def get_teacher_assignments(self, requirement):
        """
        Resolve the related TeacherAssignment manager without assuming
        a particular reverse-relation name.
        """
        for relation_name in (
            "teacher_assignments",
            "assignments",
            "teacherassignment_set",
        ):
            manager = getattr(requirement, relation_name, None)

            if manager is not None and hasattr(manager, "all"):
                return tuple(manager.all())

        return ()

    def handle(self, *args, **options):
        self.stdout.write("=" * 72)
        self.stdout.write(
            "SMARTTIMETABLE PRO - GRADE 10 PARALLEL RUNTIME AUDIT"
        )
        self.stdout.write("=" * 72)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        validate_grade10_parallel_blocks()

        self.stdout.write("=== AUTHORITATIVE BLOCKS ===")

        for description in describe_grade10_parallel_blocks():
            self.stdout.write(description)

        self.stdout.write("")
        self.stdout.write(
            f"SHARED BLOCK SLOTS = {grade10_parallel_slot_count()}"
        )
        self.stdout.write(
            f"INDEPENDENT ELECTIVE SUBJECTS = "
            f"{grade10_parallel_subject_count()}"
        )
        self.stdout.write("")

        self.stdout.write("=== GRADE 10 DATABASE REQUIREMENTS ===")

        groups = (
            InstructionalGroup.objects
            .filter(code__in=("10E", "10W"))
            .order_by("code")
        )

        if not groups.exists():
            self.stdout.write(
                "WARNING - Grade 10E / Grade 10W groups not found."
            )
            return

        total_requirements = 0
        total_assignments = 0

        for group in groups:
            group_code = getattr(group, "code", group.pk)
            group_name = getattr(group, "name", group.pk)

            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group_code} | {group_name}"
            )

            requirements = (
                LessonRequirement.objects
                .filter(
                    instructional_group=group,
                    is_active=True,
                )
                .select_related("subject")
            )

            requirements = tuple(requirements)

            if not requirements:
                self.stdout.write("  REQUIREMENTS: NONE")
                continue

            for requirement in requirements:
                total_requirements += 1

                assignments = self.get_teacher_assignments(
                    requirement
                )

                active_assignments = tuple(
                    assignment
                    for assignment in assignments
                    if getattr(
                        assignment,
                        "is_active",
                        True,
                    )
                    and getattr(
                        getattr(
                            assignment,
                            "teacher",
                            None,
                        ),
                        "is_active",
                        True,
                    )
                )

                total_assignments += len(active_assignments)

                teacher_names = ", ".join(
                    self.teacher_label(assignment.teacher)
                    for assignment in active_assignments
                    if getattr(
                        assignment,
                        "teacher",
                        None,
                    ) is not None
                ) or "NONE"

                subject = self.requirement_subject_label(
                    requirement
                )

                lessons = self.lesson_count(requirement)

                self.stdout.write(
                    f"  {subject}"
                    f" | {lessons} lessons/week"
                    f" | teachers: {teacher_names}"
                )

        self.stdout.write("")
        self.stdout.write("=== RUNTIME TOTALS ===")
        self.stdout.write(
            f"ACTIVE GRADE 10 REQUIREMENTS = "
            f"{total_requirements}"
        )
        self.stdout.write(
            f"ACTIVE TEACHER ASSIGNMENTS = "
            f"{total_assignments}"
        )

        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write(
            "GRADE 10 PARALLEL RUNTIME AUDIT COMPLETE"
        )
        self.stdout.write(
            "READ-ONLY: NO DATABASE CHANGES"
        )
        self.stdout.write("=" * 72)
