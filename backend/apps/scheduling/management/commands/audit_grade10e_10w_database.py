from django.core.management.base import BaseCommand
from apps.academics.models import InstructionalGroup, LessonRequirement
from apps.scheduling.models import TeacherAssignment


class Command(BaseCommand):
    help = "Read-only audit of Grade 10E/10W lesson requirements and teacher assignments."

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 88)
        self.stdout.write("SMARTTIMETABLE PRO - GRADE 10E / 10W DATABASE AUDIT")
        self.stdout.write("=" * 88)
        self.stdout.write("")
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES WILL BE MADE.")
        self.stdout.write("")

        groups = list(
            InstructionalGroup.objects
            .filter(code__in=("10E", "10W"))
            .select_related("teaching_group")
            .order_by("code")
        )

        self.stdout.write("INSTRUCTIONAL GROUPS")
        self.stdout.write("-" * 88)

        if not groups:
            self.stdout.write(
                self.style.ERROR(
                    "NO 10E/10W INSTRUCTIONAL GROUPS FOUND."
                )
            )
            return

        for group in groups:
            teaching_group = (
                f"{group.teaching_group.code} / "
                f"{group.teaching_group.name}"
                if group.teaching_group_id
                else "NONE"
            )

            self.stdout.write(
                f"{group.code:<6} | "
                f"{group.name:<24} | "
                f"active={str(group.is_active):<5} | "
                f"ID={group.pk} | "
                f"TeachingGroup={teaching_group}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 88)
        self.stdout.write("LESSON REQUIREMENTS")
        self.stdout.write("=" * 88)

        grand_active_requirements = 0
        grand_active_lessons = 0

        for group in groups:
            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group.name} [{group.code}]"
            )
            self.stdout.write("-" * 88)

            requirements = list(
                LessonRequirement.objects
                .filter(
                    instructional_group=group,
                )
                .select_related(
                    "subject",
                    "term",
                )
                .prefetch_related(
                    "teacher_assignments__teacher",
                )
                .order_by(
                    "is_active",
                    "subject__code",
                    "term__start_date",
                )
            )

            if not requirements:
                self.stdout.write(
                    self.style.WARNING(
                        "NO LESSON REQUIREMENTS FOUND."
                    )
                )
                continue

            active_count = 0
            active_lessons = 0

            for requirement in requirements:
                assignments = list(
                    requirement.teacher_assignments.all()
                )

                active_assignments = [
                    assignment
                    for assignment in assignments
                    if assignment.is_active
                    and assignment.teacher.is_active
                ]

                teacher_codes = ", ".join(
                    sorted(
                        assignment.teacher.employee_code
                        for assignment in active_assignments
                    )
                ) or "NONE"

                status = "ACTIVE" if requirement.is_active else "INACTIVE"

                self.stdout.write(
                    f"{status:<8} | "
                    f"{requirement.subject.code:<9} | "
                    f"{requirement.subject.name:<42} | "
                    f"{int(requirement.lessons_per_week or 0):>2}/week | "
                    f"Term={requirement.term.name} | "
                    f"Teachers={teacher_codes} | "
                    f"ReqID={requirement.pk}"
                )

                if requirement.is_active:
                    active_count += 1
                    active_lessons += int(
                        requirement.lessons_per_week or 0
                    )

                if len(active_assignments) > 1:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  !!! MULTIPLE ACTIVE TEACHERS: "
                            f"{teacher_codes}"
                        )
                    )

                if not active_assignments:
                    if requirement.is_active:
                        self.stdout.write(
                            self.style.WARNING(
                                "  !!! ACTIVE REQUIREMENT HAS NO "
                                "ACTIVE TEACHER ASSIGNMENT"
                            )
                        )

            grand_active_requirements += active_count
            grand_active_lessons += active_lessons

            self.stdout.write("")
            self.stdout.write(
                f"ACTIVE REQUIREMENTS : {active_count}"
            )
            self.stdout.write(
                f"ACTIVE WEEKLY LESSONS: {active_lessons}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 88)
        self.stdout.write("GRADE 10E / 10W SUMMARY")
        self.stdout.write("=" * 88)
        self.stdout.write(
            f"Groups audited                 : {len(groups)}"
        )
        self.stdout.write(
            f"Active requirements            : {grand_active_requirements}"
        )
        self.stdout.write(
            f"Active weekly lesson instances : {grand_active_lessons}"
        )

        self.stdout.write("")
        self.stdout.write("=" * 88)
        self.stdout.write("EXPECTED AUTHORITATIVE SUBJECT CODES")
        self.stdout.write("=" * 88)

        expected = {
            "CHEM": 3,
            "PHY": 3,
            "LIT": 3,
            "BIO": 3,
            "MUS": 4,
            "FRE": 3,
            "GEO": 5,
            "HIS": 5,
            "CS": 5,
            "AGR": 5,
            "BUS": 5,
            "EMCM": 5,
        }

        self.stdout.write(
            "CHEM=3, PHY=3, LIT=3, BIO=3, MUS=4, FRE=3, "
            "GEO=5, HIS=5, CS=5, AGR=5, BUS=5, EMCM=5"
        )

        self.stdout.write("")
        self.stdout.write(
            "This section is INFORMATIONAL ONLY. "
            "No requirements are changed."
        )

        self.stdout.write("")
        self.stdout.write("=" * 88)
        self.stdout.write("END OF READ-ONLY AUDIT")
        self.stdout.write("=" * 88)
        self.stdout.write("")
