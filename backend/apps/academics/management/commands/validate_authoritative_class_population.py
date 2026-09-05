from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Sum

from apps.academics.models import (
    InstructionalGroup,
    LessonRequirement,
)

try:
    from apps.scheduling.models import TeacherAssignment
except ImportError:
    TeacherAssignment = None


AUTHORITATIVE_GROUPS = (
    ("Form 4E", "F4E"),
    ("Form 4W", "F4W"),
    ("Form 3E", "F3E"),
    ("Form 3W", "F3W"),
    ("Grade 10E", "10E"),
    ("Grade 10W", "10W"),
    ("Grade 9E", "9E"),
    ("Grade 9W", "9W"),
    ("Grade 8E", "8E"),
    ("Grade 8W", "8W"),
)

EXPECTED_TOTAL = 49


class Command(BaseCommand):
    help = (
        "Validate the authoritative ten-class population used by "
        "SmartTimetable Pro scheduling."
    )

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 68)
        self.stdout.write(" AUTHORITATIVE SMARTTIMETABLE CLASS POPULATION")
        self.stdout.write("=" * 68)
        self.stdout.write("")

        self.stdout.write(
            "LOCKED AUTHORITATIVE GROUPS:"
        )

        for name, code in AUTHORITATIVE_GROUPS:
            self.stdout.write(f"  {code:<6} {name}")

        self.stdout.write("")
        self.stdout.write("-" * 68)

        total_requirements = 0
        total_lessons = 0
        total_assignments = 0

        missing_groups = []
        inactive_groups = []
        missing_requirements = []
        unassigned_requirements = []

        for expected_name, expected_code in AUTHORITATIVE_GROUPS:

            group = (
                InstructionalGroup.objects
                .filter(code=expected_code)
                .first()
            )

            if group is None:
                group = (
                    InstructionalGroup.objects
                    .filter(name=expected_name)
                    .first()
                )

            if group is None:
                missing_groups.append(
                    f"{expected_code} / {expected_name}"
                )

                self.stdout.write(
                    self.style.ERROR(
                        f"[MISSING GROUP] {expected_code:<6} "
                        f"{expected_name}"
                    )
                )
                continue

            requirements = (
                LessonRequirement.objects
                .filter(instructional_group=group)
                .filter(is_active=True)
                .select_related("subject", "term")
                .order_by("subject__code", "subject__name")
            )

            requirement_count = requirements.count()

            lessons = (
                requirements.aggregate(
                    total=Sum("lessons_per_week")
                ).get("total")
                or 0
            )

            assignments = 0

            if TeacherAssignment is not None:
                assignments = (
                    TeacherAssignment.objects
                    .filter(
                        lesson_requirement__in=requirements,
                        is_active=True,
                    )
                    .count()
                )

            total_requirements += requirement_count
            total_lessons += lessons
            total_assignments += assignments

            state = (
                "ACTIVE"
                if group.is_active
                else "INACTIVE"
            )

            self.stdout.write(
                f"[{state:<8}] "
                f"{expected_code:<6} "
                f"{expected_name:<12} "
                f"requirements={requirement_count:<3} "
                f"lessons/week={lessons:<3} "
                f"teacher_assignments={assignments:<3}"
            )

            if not group.is_active:
                inactive_groups.append(
                    f"{expected_code} / {expected_name}"
                )

            if requirement_count == 0:
                missing_requirements.append(
                    f"{expected_code} / {expected_name}"
                )

            if TeacherAssignment is not None:
                for requirement in requirements:
                    assignment_count = (
                        TeacherAssignment.objects
                        .filter(
                            lesson_requirement=requirement,
                            is_active=True,
                        )
                        .count()
                    )

                    if assignment_count != 1:
                        subject = getattr(
                            requirement.subject,
                            "name",
                            str(requirement.subject),
                        )

                        unassigned_requirements.append(
                            f"{expected_name}: {subject} "
                            f"(active teacher assignments="
                            f"{assignment_count})"
                        )

        self.stdout.write("")
        self.stdout.write("-" * 68)
        self.stdout.write("POPULATION TOTALS")
        self.stdout.write("-" * 68)

        self.stdout.write(
            f"  Authoritative groups:       "
            f"{len(AUTHORITATIVE_GROUPS)}"
        )
        self.stdout.write(
            f"  Active requirements:        "
            f"{total_requirements}"
        )
        self.stdout.write(
            f"  Required lessons/week:      "
            f"{total_lessons}"
        )
        self.stdout.write(
            f"  Active teacher assignments: "
            f"{total_assignments}"
        )
        self.stdout.write(
            f"  Required solver target:     "
            f"{EXPECTED_TOTAL}"
        )

        self.stdout.write("")

        if missing_groups:
            self.stdout.write(
                self.style.ERROR("MISSING AUTHORITATIVE GROUPS:")
            )
            for item in missing_groups:
                self.stdout.write(
                    self.style.ERROR(f"  - {item}")
                )

        if inactive_groups:
            self.stdout.write(
                self.style.ERROR("INACTIVE AUTHORITATIVE GROUPS:")
            )
            for item in inactive_groups:
                self.stdout.write(
                    self.style.ERROR(f"  - {item}")
                )

        if missing_requirements:
            self.stdout.write(
                self.style.ERROR(
                    "AUTHORITATIVE GROUPS WITH NO ACTIVE REQUIREMENTS:"
                )
            )
            for item in missing_requirements:
                self.stdout.write(
                    self.style.ERROR(f"  - {item}")
                )

        if unassigned_requirements:
            self.stdout.write(
                self.style.ERROR(
                    "ACTIVE REQUIREMENTS WITHOUT EXACTLY ONE "
                    "ACTIVE TEACHER ASSIGNMENT:"
                )
            )
            for item in unassigned_requirements:
                self.stdout.write(
                    self.style.ERROR(f"  - {item}")
                )

        self.stdout.write("")

        if total_lessons != EXPECTED_TOTAL:
            raise CommandError(
                "AUTHORITATIVE POPULATION GATE FAILED: "
                f"database currently contains {total_lessons} "
                f"required lessons/week, but the locked solver "
                f"target is {EXPECTED_TOTAL}. "
                "No data was modified."
            )

        if missing_groups:
            raise CommandError(
                "AUTHORITATIVE POPULATION GATE FAILED: "
                "one or more authoritative instructional groups "
                "are missing. No data was modified."
            )

        if inactive_groups:
            raise CommandError(
                "AUTHORITATIVE POPULATION GATE FAILED: "
                "one or more authoritative instructional groups "
                "are inactive. No data was modified."
            )

        if missing_requirements:
            raise CommandError(
                "AUTHORITATIVE POPULATION GATE FAILED: "
                "one or more authoritative groups have no active "
                "lesson requirements. No data was modified."
            )

        if unassigned_requirements:
            raise CommandError(
                "AUTHORITATIVE POPULATION GATE FAILED: "
                "one or more active lesson requirements do not have "
                "exactly one active teacher assignment. "
                "No data was modified."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "AUTHORITATIVE POPULATION GATE PASSED."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"The ten authoritative classes provide exactly "
                f"{EXPECTED_TOTAL} required lessons/week."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "The scheduling solver may now consume this "
                "database population without class-name hard-coding."
            )
        )

        self.stdout.write("")
        self.stdout.write("=" * 68)
        self.stdout.write(" VALIDATION COMPLETE — NO DATA MODIFIED")
        self.stdout.write("=" * 68)
        self.stdout.write("")