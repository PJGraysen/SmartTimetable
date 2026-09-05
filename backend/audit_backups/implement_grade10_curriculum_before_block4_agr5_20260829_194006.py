from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academics.models import (
    InstructionalGroup,
    LessonRequirement,
    Subject,
)
from apps.core.models import Term


class Command(BaseCommand):
    help = (
        "Implement the authoritative Grade 10 four-block elective "
        "curriculum for active Grade 10E and Grade 10W instructional "
        "groups without modifying the scheduling solver."
    )

    # ------------------------------------------------------------------
    # AUTHORITATIVE SUBJECT MASTER
    # ------------------------------------------------------------------

    SUBJECTS = {
        "CHEM": ("Chemistry", "CHEM"),
        "PHY": ("Physics", "PHY"),
        "LIT": ("Literature in English", "LIT"),
        "BIO": ("Biology", "BIO"),
        "MUS": ("Music", "MUS"),
        "FRE": ("French", "FRE"),
        "GEO": ("Geography", "GEO"),
        "HIS": ("History", "HIS"),
        "CS": ("Computer Science", "CS"),
        "AGR": ("Agriculture", "AGR"),
        "BUS": ("Business Studies", "BUS"),
        "EMCM": (
            "Essential Mathematics / Core Mathematics",
            "EMCM",
        ),
    }

    # ------------------------------------------------------------------
    # OFFICIAL GRADE 10 ELECTIVE BLOCKS
    #
    # HIS and CS remain members of BLOCK 3.
    # They are NOT standalone requirements.
    # ------------------------------------------------------------------

    ELECTIVE_BLOCKS = (
        ("BLOCK_2", "CHEM / PHY / LIT", ("CHEM", "PHY", "LIT")),
        ("BLOCK_1", "BIO / MU / FRE", ("BIO", "MUS", "FRE")),
        ("BLOCK_3", "GEO / HIS / COMP", ("GEO", "HIS", "CS")),
        ("BLOCK_4", "A / BS", ("AGR", "BUS")),
        ("CORE", "E.M / CM", ("EMCM",)),
    )

    # ------------------------------------------------------------------
    # AUTHORITATIVE WEEKLY LESSON REQUIREMENTS
    #
    # These values are per subject, not one global value.
    #
    # In particular:
    #   HIS = 4/week
    #   CS  = 4/week
    #
    # Block membership and weekly frequency are separate concepts.
    # ------------------------------------------------------------------

    WEEKLY_LESSONS = {
        "CHEM": 3,
        "PHY": 3,
        "LIT": 3,

        "BIO": 3,
        "MUS": 4,
        "FRE": 3,

        "GEO": 3,
        "HIS": 4,
        "CS": 4,

        "AGR": 3,
        "BUS": 5,

        "EMCM": 5,
    }

    # ------------------------------------------------------------------
    # AUTHORITATIVE ACTIVE GRADE 10 GROUP CODES
    # ------------------------------------------------------------------

    GRADE10_GROUP_CODES = ("10E", "10W")

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write("AUTHORITATIVE GRADE 10 CURRICULUM IMPLEMENTATION")
        self.stdout.write("=" * 72)
        self.stdout.write("")

        # --------------------------------------------------------------
        # LOCATE ACTIVE GRADE 10 INSTRUCTIONAL GROUPS
        # --------------------------------------------------------------

        groups = list(
            InstructionalGroup.objects
            .filter(
                code__in=self.GRADE10_GROUP_CODES,
                is_active=True,
            )
            .select_related("teaching_group")
            .order_by("code")
        )

        if not groups:
            raise CommandError(
                "No active Grade 10 instructional groups were found. "
                "Expected active groups with codes 10E and/or 10W."
            )

        found_codes = {group.code for group in groups}
        missing_codes = [
            code
            for code in self.GRADE10_GROUP_CODES
            if code not in found_codes
        ]

        self.stdout.write("ACTIVE GRADE 10 INSTRUCTIONAL GROUPS:")
        self.stdout.write("")

        for group in groups:
            self.stdout.write(
                f"  {group.code:<5} | "
                f"{group.name:<20} | "
                f"ID={group.pk}"
            )

        if missing_codes:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: The following expected Grade 10 group(s) "
                    "are not currently active: "
                    + ", ".join(missing_codes)
                )
            )

        self.stdout.write("")

        # --------------------------------------------------------------
        # ACTIVE TERM
        # --------------------------------------------------------------

        term = (
            Term.objects
            .filter(is_active=True)
            .order_by("-created_at")
            .first()
        )

        if term is None:
            raise CommandError(
                "No active academic term exists."
            )

        self.stdout.write(
            f"Active term: {term.name} [{term.id}]"
        )
        self.stdout.write("")

        # --------------------------------------------------------------
        # AUTHORITATIVE FREQUENCY VALIDATION
        # --------------------------------------------------------------

        missing_frequency_definitions = [
            code
            for code in self.SUBJECTS
            if code not in self.WEEKLY_LESSONS
        ]

        if missing_frequency_definitions:
            raise CommandError(
                "Missing authoritative weekly lesson frequencies for: "
                + ", ".join(missing_frequency_definitions)
            )

        self.stdout.write("=" * 72)
        self.stdout.write("AUTHORITATIVE WEEKLY LESSON FREQUENCIES")
        self.stdout.write("=" * 72)
        self.stdout.write("")

        for code, lessons in self.WEEKLY_LESSONS.items():
            name = self.SUBJECTS[code][0]
            self.stdout.write(
                f"{code:<6} {name:<42} {lessons:>2} lessons/week"
            )

        # --------------------------------------------------------------
        # SUBJECT MASTER
        # --------------------------------------------------------------

        created_subjects = []
        reused_subjects = []

        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write("SUBJECT MASTER")
        self.stdout.write("=" * 72)
        self.stdout.write("")

        for code, (name, _) in self.SUBJECTS.items():
            subject = (
                Subject.objects
                .filter(code=code)
                .first()
            )

            if subject is None:
                subject = Subject.objects.create(
                    code=code,
                    name=name,
                    is_active=True,
                )

                created_subjects.append(code)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"CREATED SUBJECT  {code:<6} {name}"
                    )
                )
            else:
                reused_subjects.append(code)

                if not subject.is_active:
                    subject.is_active = True
                    subject.save(
                        update_fields=["is_active", "updated_at"]
                    )

                self.stdout.write(
                    f"REUSED SUBJECT   {code:<6} {subject.name}"
                )

        # --------------------------------------------------------------
        # LESSON REQUIREMENTS
        #
        # Apply the same authoritative Grade 10 curriculum to EACH
        # active Grade 10 instructional group.
        #
        # Block membership is preserved.
        # Weekly frequency is controlled by WEEKLY_LESSONS.
        # --------------------------------------------------------------

        created_requirements = []
        existing_requirements = []
        reactivated_requirements = []
        corrected_requirements = []

        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write("GRADE 10 LESSON REQUIREMENTS")
        self.stdout.write("=" * 72)

        for group in groups:
            self.stdout.write("")
            self.stdout.write(
                self.style.HTTP_INFO(
                    f"GROUP: {group.name} [{group.code}]"
                )
            )

            for block_code, block_name, subject_codes in self.ELECTIVE_BLOCKS:
                self.stdout.write("")
                self.stdout.write(
                    self.style.HTTP_INFO(
                        f"{block_code}: {block_name}"
                    )
                )

                for code in subject_codes:
                    subject = Subject.objects.get(code=code)
                    weekly_lessons = self.WEEKLY_LESSONS[code]

                    requirement = (
                        LessonRequirement.objects
                        .filter(
                            term=term,
                            instructional_group=group,
                            subject=subject,
                        )
                        .first()
                    )

                    if requirement is None:
                        requirement = LessonRequirement.objects.create(
                            term=term,
                            instructional_group=group,
                            subject=subject,
                            lessons_per_week=weekly_lessons,
                            is_active=True,
                        )

                        created_requirements.append(
                            (
                                group.code,
                                code,
                                subject.name,
                                weekly_lessons,
                            )
                        )

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"CREATED REQUIREMENT "
                                f"{group.code:<5} "
                                f"{code:<6} "
                                f"{subject.name:<40} "
                                f"{weekly_lessons} lessons/week"
                            )
                        )

                    else:
                        old_lessons = int(
                            requirement.lessons_per_week or 0
                        )

                        was_inactive = not requirement.is_active

                        changed = False
                        update_fields = []

                        if old_lessons != weekly_lessons:
                            requirement.lessons_per_week = weekly_lessons
                            update_fields.append("lessons_per_week")
                            changed = True

                            corrected_requirements.append(
                                (
                                    group.code,
                                    code,
                                    subject.name,
                                    old_lessons,
                                    weekly_lessons,
                                )
                            )

                        if was_inactive:
                            requirement.is_active = True
                            update_fields.append("is_active")
                            changed = True

                            reactivated_requirements.append(
                                (
                                    group.code,
                                    code,
                                    subject.name,
                                )
                            )

                        if changed:
                            update_fields.append("updated_at")
                            requirement.save(
                                update_fields=update_fields
                            )

                            if old_lessons != weekly_lessons:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"CORRECTED REQUIREMENT "
                                        f"{group.code:<5} "
                                        f"{code:<6} "
                                        f"{subject.name:<40} "
                                        f"{old_lessons} -> "
                                        f"{weekly_lessons} lessons/week"
                                    )
                                )
                            elif was_inactive:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"REACTIVATED REQUIREMENT "
                                        f"{group.code:<5} "
                                        f"{code:<6} "
                                        f"{subject.name:<40} "
                                        f"{weekly_lessons} lessons/week"
                                    )
                                )
                        else:
                            existing_requirements.append(
                                (
                                    group.code,
                                    code,
                                    subject.name,
                                    weekly_lessons,
                                )
                            )

                            self.stdout.write(
                                f"EXISTING REQUIREMENT "
                                f"{group.code:<5} "
                                f"{code:<6} "
                                f"{subject.name:<40} "
                                f"{weekly_lessons} lessons/week"
                            )

        # --------------------------------------------------------------
        # FINAL DATABASE AUDIT
        #
        # This audits only the authoritative subjects managed by this
        # command. Existing standalone Grade 10 requirements such as
        # ENG, KIS, CRE, CSL, ICT, PE and PRP remain part of the active
        # Grade 10 curriculum and are not deleted or deactivated here.
        # --------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write("FINAL GRADE 10 CURRICULUM AUDIT")
        self.stdout.write("=" * 72)

        grand_total_lessons = 0
        grand_total_requirements = 0
        missing_curriculum = []
        incorrect_frequencies = []

        for group in groups:
            requirements = list(
                LessonRequirement.objects
                .filter(
                    term=term,
                    instructional_group=group,
                    is_active=True,
                )
                .select_related("subject")
                .order_by("subject__code")
            )

            active_codes = {
                requirement.subject.code
                for requirement in requirements
            }

            required_codes = set(self.SUBJECTS.keys())

            missing = sorted(
                required_codes - active_codes
            )

            if missing:
                missing_curriculum.append(
                    (group.code, missing)
                )

            group_total_lessons = 0

            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group.name} [{group.code}]"
            )
            self.stdout.write("-" * 72)

            for requirement in requirements:
                lessons = int(
                    requirement.lessons_per_week or 0
                )

                group_total_lessons += lessons

                code = requirement.subject.code

                if code in self.WEEKLY_LESSONS:
                    expected = self.WEEKLY_LESSONS[code]

                    if lessons != expected:
                        incorrect_frequencies.append(
                            (
                                group.code,
                                code,
                                lessons,
                                expected,
                            )
                        )

                self.stdout.write(
                    f"{code:<8} "
                    f"{requirement.subject.name:<42} "
                    f"{lessons:>2} lessons/week"
                )

            grand_total_requirements += len(requirements)
            grand_total_lessons += group_total_lessons

            self.stdout.write("")
            self.stdout.write(
                f"ACTIVE REQUIREMENTS FOR {group.code}: "
                f"{len(requirements)}"
            )
            self.stdout.write(
                f"TOTAL WEEKLY INSTANCES FOR {group.code}: "
                f"{group_total_lessons}"
            )

        # --------------------------------------------------------------
        # VERIFY OFFICIAL ELECTIVE SUBJECTS
        # --------------------------------------------------------------

        if missing_curriculum:
            details = []

            for group_code, missing in missing_curriculum:
                details.append(
                    f"{group_code}: {', '.join(missing)}"
                )

            raise CommandError(
                "Grade 10 elective curriculum is still missing active "
                "requirements: "
                + " | ".join(details)
            )

        if incorrect_frequencies:
            details = [
                (
                    f"{group_code} {subject_code}: "
                    f"{actual}/week instead of {expected}/week"
                )
                for (
                    group_code,
                    subject_code,
                    actual,
                    expected,
                ) in incorrect_frequencies
            ]

            raise CommandError(
                "Authoritative Grade 10 weekly frequencies are incorrect: "
                + " | ".join(details)
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "PASS: all official Grade 10 elective requirements "
                "are active and have the authoritative weekly "
                "frequencies."
            )
        )

        # --------------------------------------------------------------
        # TEACHER ASSIGNMENT AUDIT
        #
        # This command does not invent teachers.
        # Existing authoritative active assignments are reported.
        # Missing assignments remain visible for later assignment
        # through the frontend/assignment workflow.
        # --------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write("TEACHER ASSIGNMENT STATUS")
        self.stdout.write("=" * 72)

        missing_teacher_assignments = []

        for group in groups:
            requirements = list(
                LessonRequirement.objects
                .filter(
                    term=term,
                    instructional_group=group,
                    is_active=True,
                )
                .select_related("subject")
                .order_by("subject__code")
            )

            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group.code}"
            )

            for requirement in requirements:
                assignments = list(
                    requirement.teacher_assignments
                    .filter(
                        is_active=True,
                        teacher__is_active=True,
                    )
                    .select_related("teacher")
                )

                if not assignments:
                    missing_teacher_assignments.append(
                        (
                            group.code,
                            requirement.subject.code,
                        )
                    )

                    self.stdout.write(
                        self.style.WARNING(
                            f"NO ACTIVE TEACHER: "
                            f"{group.code} "
                            f"{requirement.subject.code} "
                            f"{requirement.subject.name}"
                        )
                    )
                else:
                    teacher_codes = ", ".join(
                        assignment.teacher.employee_code
                        for assignment in assignments
                    )

                    self.stdout.write(
                        f"ASSIGNED: "
                        f"{group.code:<5} "
                        f"{requirement.subject.code:<6} "
                        f"{teacher_codes}"
                    )

        # --------------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write("GRADE 10 CURRICULUM IMPLEMENTATION COMPLETE")
        self.stdout.write("=" * 72)

        self.stdout.write("")
        self.stdout.write(
            f"Active Grade 10 groups       : {len(groups)}"
        )
        self.stdout.write(
            f"New subjects created         : {len(created_subjects)}"
        )
        self.stdout.write(
            f"New requirements created     : "
            f"{len(created_requirements)}"
        )
        self.stdout.write(
            f"Requirements reactivated    : "
            f"{len(reactivated_requirements)}"
        )
        self.stdout.write(
            f"Requirements frequency-fixed : "
            f"{len(corrected_requirements)}"
        )
        self.stdout.write(
            f"Existing requirements reused : "
            f"{len(existing_requirements)}"
        )
        self.stdout.write(
            f"Active requirements total    : "
            f"{grand_total_requirements}"
        )
        self.stdout.write(
            f"Weekly lesson instances total: "
            f"{grand_total_lessons}"
        )

        if missing_teacher_assignments:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "IMPORTANT: The following active requirements "
                    "still need authoritative teacher assignments:"
                )
            )

            for group_code, subject_code in missing_teacher_assignments:
                self.stdout.write(
                    f"  - {group_code}: {subject_code}"
                )

            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "No teacher was invented or assigned automatically."
                )
            )
        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "PASS: every active Grade 10 requirement "
                    "has an active teacher assignment."
                )
            )

        self.stdout.write("")
        self.stdout.write(
            "No solver files were modified."
        )
        self.stdout.write(
            "No frontend files were modified."
        )
        self.stdout.write("=" * 72)
