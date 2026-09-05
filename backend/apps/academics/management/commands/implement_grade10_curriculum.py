from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academics.models import (
    InstructionalGroup,
    LessonRequirement,
    Subject,
)
from apps.core.models import Term
from apps.scheduling.models import TeacherAssignment
from apps.users.models import Teacher


class Command(BaseCommand):
    """
    SINGLE AUTHORITATIVE GRADE 10 CURRICULUM IMPLEMENTATION.

    This command is the only management command responsible for
    implementing the Grade 10 academic business rules.

    It manages only:
        - Grade 10E and Grade 10W
        - Grade 10 subject master
        - Grade 10 lesson requirements
        - Grade 10 elective block definitions
        - authoritative Grade 10 teacher assignments
        - temporary inactivity of French because no teacher exists

    It does NOT:
        - modify solver code
        - create timetable entries
        - modify timetable periods
        - modify breaks
        - modify Assembly
        - modify Prayers
        - modify Activities
        - invent teachers
        - modify unrelated classes
    """

    help = (
        "Implement the authoritative Grade 10 academic curriculum "
        "for Grade 10E and Grade 10W."
    )

    # ================================================================
    # AUTHORITATIVE SUBJECT MASTER
    # ================================================================

    SUBJECTS = {
        "ENG": "English",
        "KIS": "Kiswahili",
        "EMCM": "Essential Mathematics / Core Mathematics",
        "CRE": "Christian Religious Education",
        "PE": "Physical Education",
        "CSL": "Community Service Learning",
        "ICT": "ICT Skills",
        "PRP": "Pastoral/Religious Programme",
        "GST": "Group Study / Life Skills",
        "BIO": "Biology",
        "MUS": "Music",
        "FRE": "French",
        "CHEM": "Chemistry",
        "PHY": "Physics",
        "LIT": "Literature in English",
        "GEO": "Geography",
        "HIS": "History",
        "CS": "Computer Science",
        "BUS": "Business Studies",
        "AGR": "Agriculture",
    }

    # ================================================================
    # AUTHORITATIVE WEEKLY REQUIREMENTS
    # ================================================================

    WEEKLY_LESSONS = {
        "ENG": 5,
        "KIS": 5,
        "EMCM": 5,
        "CRE": 4,
        "PE": 3,
        "CSL": 3,
        "ICT": 2,
        "PRP": 1,
        "GST": 1,

        "BIO": 5,
        "MUS": 5,
        "FRE": 5,

        "CHEM": 5,
        "PHY": 5,
        "LIT": 5,

        "GEO": 5,
        "HIS": 5,
        "CS": 5,

        "BUS": 5,
        "AGR": 5,
    }

    # ================================================================
    # AUTHORITATIVE ELECTIVE BLOCKS
    #
    # Subjects in the same block occupy the SAME five timetable
    # periods. They remain separate LessonRequirements and retain
    # independent teachers/subject identities.
    # ================================================================

    ELECTIVE_BLOCKS = (
        (
            "OPTION_1",
            "BIO / MUS / FRE",
            ("BIO", "MUS", "FRE"),
        ),
        (
            "OPTION_2",
            "CHEM / PHY / LIT",
            ("CHEM", "PHY", "LIT"),
        ),
        (
            "OPTION_3",
            "GEO / HIS / CS",
            ("GEO", "HIS", "CS"),
        ),
        (
            "OPTION_4",
            "BUS / AGR",
            ("BUS", "AGR"),
        ),
    )

    # ================================================================
    # AUTHORITATIVE GRADE 10 GROUPS
    # ================================================================

    GRADE10_GROUP_CODES = ("10E", "10W")

    # ================================================================
    # SUBJECTS CURRENTLY WITHOUT A TEACHER
    #
    # French is part of OPTION_1 but is temporarily not schedulable.
    # GST remains a required one-slot component but no teacher is
    # invented here.
    # ================================================================

    TEMPORARILY_INACTIVE_SUBJECTS = {
        "FRE",
    }

    # ================================================================
    # AUTHORITATIVE MULTI-TEACHER ASSIGNMENTS
    #
    # These multiple teachers are intentional and MUST NOT be reduced
    # to one teacher.
    # ================================================================

    MULTI_TEACHER_ASSIGNMENTS = {
        "ENG": ("T011", "T015"),
        "KIS": ("T001", "T020"),
        "EMCM": ("T004", "T013"),
        "CRE": ("T002", "T006"),
    }

    # ================================================================
    # AUTHORITATIVE SINGLE-TEACHER ASSIGNMENTS
    #
    # Only subjects explicitly listed here are enforced.
    # Other existing Grade 10 assignments are preserved.
    # ================================================================

    SINGLE_TEACHER_ASSIGNMENTS = {
        "AGR": "T010",
        "BIO": "T016",
        "BUS": "T019",
        "CHEM": "T005",
        "CS": "T019",
        "CSL": "T016",
        "GEO": "T018",
        "HIS": "T006",
        "ICT": "T019",
        "LIT": "T011",
        "MUS": "T019",
        "PE": "T014",
        "PHY": "T009",
        "PRP": "T001",
    }

    # GST and FRE intentionally have no teacher assignment here.

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write(
            "SMARTTIMETABLE PRO - AUTHORITATIVE GRADE 10 CURRICULUM"
        )
        self.stdout.write("=" * 80)
        self.stdout.write("")

        # ============================================================
        # ACTIVE TERM
        # ============================================================

        term = (
            Term.objects
            .filter(is_active=True)
            .order_by("-start_date", "-created_at")
            .first()
        )

        if term is None:
            raise CommandError("No active academic term exists.")

        self.stdout.write(
            f"ACTIVE TERM: {term.name} [{term.id}]"
        )
        self.stdout.write("")

        # ============================================================
        # AUTHORITATIVE GROUPS
        # ============================================================

        groups = list(
            InstructionalGroup.objects
            .filter(
                code__in=self.GRADE10_GROUP_CODES,
                is_active=True,
            )
            .order_by("code")
        )

        found_codes = {group.code for group in groups}

        if found_codes != set(self.GRADE10_GROUP_CODES):
            missing = sorted(
                set(self.GRADE10_GROUP_CODES) - found_codes
            )

            raise CommandError(
                "Both Grade 10E and Grade 10W must be active. "
                "Missing: " + ", ".join(missing)
            )

        self.stdout.write("AUTHORITATIVE INSTRUCTIONAL GROUPS:")

        for group in groups:
            self.stdout.write(
                f"  {group.code:<5} | {group.name}"
            )

        # ============================================================
        # SUBJECT MASTER
        # ============================================================

        self.stdout.write("")
        self.stdout.write("-" * 80)
        self.stdout.write("SUBJECT MASTER")
        self.stdout.write("-" * 80)

        subjects = {}
        subjects_created = 0
        subjects_reactivated = 0

        for code, name in self.SUBJECTS.items():
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "is_active": True,
                },
            )

            if created:
                subjects_created += 1
            else:
                changed = False
                update_fields = []

                if subject.name != name:
                    subject.name = name
                    update_fields.append("name")
                    changed = True

                if not subject.is_active:
                    subject.is_active = True
                    update_fields.append("is_active")
                    changed = True
                    subjects_reactivated += 1

                if changed:
                    update_fields.append("updated_at")
                    subject.save(update_fields=update_fields)

            subjects[code] = subject

            self.stdout.write(
                f"  {code:<6} {subject.name}"
            )

        # ============================================================
        # VALIDATE DEFINITIONS
        # ============================================================

        missing_frequencies = sorted(
            set(self.SUBJECTS) - set(self.WEEKLY_LESSONS)
        )

        if missing_frequencies:
            raise CommandError(
                "Missing authoritative frequencies for: "
                + ", ".join(missing_frequencies)
            )

        # ============================================================
        # LESSON REQUIREMENTS
        # ============================================================

        self.stdout.write("")
        self.stdout.write("-" * 80)
        self.stdout.write("GRADE 10 LESSON REQUIREMENTS")
        self.stdout.write("-" * 80)

        requirements = {}

        requirements_created = 0
        requirements_corrected = 0
        requirements_reactivated = 0
        requirements_deactivated = 0
        requirements_unchanged = 0

        for group in groups:
            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group.code} | {group.name}"
            )

            for code, subject in subjects.items():
                expected_lessons = self.WEEKLY_LESSONS[code]

                should_be_active = (
                    code not in self.TEMPORARILY_INACTIVE_SUBJECTS
                )

                requirement, created = (
                    LessonRequirement.objects.get_or_create(
                        term=term,
                        instructional_group=group,
                        subject=subject,
                        defaults={
                            "lessons_per_week": expected_lessons,
                            "is_active": should_be_active,
                        },
                    )
                )

                requirements[(group.code, code)] = requirement

                if created:
                    requirements_created += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  CREATED   {code:<6} "
                            f"{expected_lessons}/week "
                            f"{'ACTIVE' if should_be_active else 'INACTIVE'}"
                        )
                    )
                    continue

                changed = False
                update_fields = []

                if requirement.lessons_per_week != expected_lessons:
                    requirement.lessons_per_week = expected_lessons
                    update_fields.append("lessons_per_week")
                    changed = True
                    requirements_corrected += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  CORRECTED {code:<6} "
                            f"-> {expected_lessons}/week"
                        )
                    )

                if requirement.is_active != should_be_active:
                    requirement.is_active = should_be_active
                    update_fields.append("is_active")
                    changed = True

                    if should_be_active:
                        requirements_reactivated += 1
                    else:
                        requirements_deactivated += 1

                if changed:
                    update_fields.append("updated_at")
                    requirement.save(
                        update_fields=update_fields
                    )
                else:
                    requirements_unchanged += 1

        # ============================================================
        # TEACHER MASTER
        # ============================================================

        teacher_codes = set()

        for codes in self.MULTI_TEACHER_ASSIGNMENTS.values():
            teacher_codes.update(codes)

        teacher_codes.update(
            self.SINGLE_TEACHER_ASSIGNMENTS.values()
        )

        teachers = {
            teacher.employee_code: teacher
            for teacher in Teacher.objects.filter(
                employee_code__in=teacher_codes,
                is_active=True,
            )
        }

        missing_teachers = sorted(
            teacher_codes - set(teachers)
        )

        if missing_teachers:
            raise CommandError(
                "Required authoritative active teachers are missing: "
                + ", ".join(missing_teachers)
            )

        # ============================================================
        # AUTHORITATIVE TEACHER ASSIGNMENTS
        # ============================================================

        self.stdout.write("")
        self.stdout.write("-" * 80)
        self.stdout.write("AUTHORITATIVE TEACHER ASSIGNMENTS")
        self.stdout.write("-" * 80)

        assignments_created = 0
        assignments_activated = 0
        assignments_deactivated = 0

        for group in groups:

            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group.code}"
            )

            # --------------------------------------------------------
            # Multi-teacher subjects
            # --------------------------------------------------------

            for subject_code, authoritative_codes in (
                self.MULTI_TEACHER_ASSIGNMENTS.items()
            ):
                requirement = requirements[
                    (group.code, subject_code)
                ]

                # Deactivate every existing assignment for this
                # requirement first. Then explicitly restore the
                # authoritative active teacher set.
                existing_assignments = (
                    TeacherAssignment.objects
                    .filter(
                        lesson_requirement=requirement,
                        is_active=True,
                    )
                )

                assignments_deactivated += (
                    existing_assignments.update(
                        is_active=False
                    )
                )

                for teacher_code in authoritative_codes:
                    assignment, created = (
                        TeacherAssignment.objects.update_or_create(
                            lesson_requirement=requirement,
                            teacher=teachers[teacher_code],
                            defaults={
                                "is_active": True,
                            },
                        )
                    )

                    if created:
                        assignments_created += 1
                    else:
                        assignments_activated += 1

                self.stdout.write(
                    f"  {subject_code:<6} -> "
                    f"{','.join(authoritative_codes)}"
                )

            # --------------------------------------------------------
            # Single-teacher subjects
            # --------------------------------------------------------

            for subject_code, teacher_code in (
                self.SINGLE_TEACHER_ASSIGNMENTS.items()
            ):
                requirement = requirements[
                    (group.code, subject_code)
                ]

                existing_assignments = (
                    TeacherAssignment.objects
                    .filter(
                        lesson_requirement=requirement,
                        is_active=True,
                    )
                )

                assignments_deactivated += (
                    existing_assignments
                    .exclude(
                        teacher=teachers[teacher_code]
                    )
                    .update(
                        is_active=False
                    )
                )

                assignment, created = (
                    TeacherAssignment.objects.update_or_create(
                        lesson_requirement=requirement,
                        teacher=teachers[teacher_code],
                        defaults={
                            "is_active": True,
                        },
                    )
                )

                if created:
                    assignments_created += 1
                else:
                    assignments_activated += 1

                self.stdout.write(
                    f"  {subject_code:<6} -> {teacher_code}"
                )

            # --------------------------------------------------------
            # French: explicitly no active teacher
            # --------------------------------------------------------

            french_requirement = requirements[
                (group.code, "FRE")
            ]

            french_disabled = (
                TeacherAssignment.objects
                .filter(
                    lesson_requirement=french_requirement,
                    is_active=True,
                )
                .update(is_active=False)
            )

            assignments_deactivated += french_disabled

            self.stdout.write(
                "  FRE    -> NONE (temporarily inactive)"
            )

            # --------------------------------------------------------
            # GST: no teacher invented
            # --------------------------------------------------------

            gst_requirement = requirements[
                (group.code, "GST")
            ]

            self.stdout.write(
                "  GST    -> NONE (teacher not assigned)"
            )

        # ============================================================
        # 49-LESSON CONTRACT
        #
        # Core / standalone / group-study:
        #
        # ENG 5
        # KIS 5
        # EMCM 5
        # CRE 4
        # PE 3
        # CSL 3
        # ICT 2
        # PRP 1
        # GST 1
        #
        # = 29
        #
        # Four elective blocks x 5 shared slots:
        #
        # OPTION 1 = 5
        # OPTION 2 = 5
        # OPTION 3 = 5
        # OPTION 4 = 5
        #
        # = 20
        #
        # 29 + 20 = 49
        # ============================================================

        core_slot_total = sum(
            self.WEEKLY_LESSONS[code]
            for code in (
                "ENG",
                "KIS",
                "EMCM",
                "CRE",
                "PE",
                "CSL",
                "ICT",
                "PRP",
                "GST",
            )
        )

        elective_slot_total = (
            len(self.ELECTIVE_BLOCKS) * 5
        )

        effective_teaching_slots = (
            core_slot_total + elective_slot_total
        )

        self.stdout.write("")
        self.stdout.write("-" * 80)
        self.stdout.write("49-LESSON CONTRACT")
        self.stdout.write("-" * 80)
        self.stdout.write(
            f"  Core / standalone / group-study slots : "
            f"{core_slot_total}"
        )
        self.stdout.write(
            f"  Elective block slots                   : "
            f"{elective_slot_total}"
        )
        self.stdout.write(
            f"  EFFECTIVE TEACHING SLOTS               : "
            f"{effective_teaching_slots}"
        )

        if effective_teaching_slots != 49:
            raise CommandError(
                "AUTHORITATIVE 49-LESSON CONTRACT FAILED: "
                f"{effective_teaching_slots} calculated."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "  PASS: exactly 49 effective teaching slots/week."
            )
        )

        # ============================================================
        # FINAL DATABASE AUDIT
        # ============================================================

        self.stdout.write("")
        self.stdout.write("-" * 80)
        self.stdout.write("FINAL DATABASE AUDIT")
        self.stdout.write("-" * 80)

        errors = []

        for group in groups:
            for code, expected_lessons in (
                self.WEEKLY_LESSONS.items()
            ):
                requirement = requirements[
                    (group.code, code)
                ]

                expected_active = (
                    code not in self.TEMPORARILY_INACTIVE_SUBJECTS
                )

                if requirement.lessons_per_week != expected_lessons:
                    errors.append(
                        f"{group.code}: {code} frequency is "
                        f"{requirement.lessons_per_week}, "
                        f"expected {expected_lessons}"
                    )

                if requirement.is_active != expected_active:
                    errors.append(
                        f"{group.code}: {code} active state is "
                        f"{requirement.is_active}, "
                        f"expected {expected_active}"
                    )

            # --------------------------------------------------------
            # Verify multi-teacher subjects
            # --------------------------------------------------------

            for subject_code, expected_codes in (
                self.MULTI_TEACHER_ASSIGNMENTS.items()
            ):
                requirement = requirements[
                    (group.code, subject_code)
                ]

                actual_codes = set(
                    TeacherAssignment.objects
                    .filter(
                        lesson_requirement=requirement,
                        is_active=True,
                        teacher__is_active=True,
                    )
                    .values_list(
                        "teacher__employee_code",
                        flat=True,
                    )
                )

                if actual_codes != set(expected_codes):
                    errors.append(
                        f"{group.code}: {subject_code} teachers "
                        f"are {','.join(sorted(actual_codes)) or 'NONE'}, "
                        f"expected {','.join(expected_codes)}"
                    )

            # --------------------------------------------------------
            # Verify French has no active assignment
            # --------------------------------------------------------

            french_requirement = requirements[
                (group.code, "FRE")
            ]

            french_active_teacher_count = (
                TeacherAssignment.objects
                .filter(
                    lesson_requirement=french_requirement,
                    is_active=True,
                    teacher__is_active=True,
                )
                .count()
            )

            if french_active_teacher_count:
                errors.append(
                    f"{group.code}: FRE has active teacher assignments"
                )

        if errors:
            raise CommandError(
                "AUTHORITATIVE GRADE 10 DATABASE AUDIT FAILED:\n"
                + "\n".join(
                    f"  - {error}"
                    for error in errors
                )
            )

        # ============================================================
        # FINAL SUMMARY
        # ============================================================

        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write("IMPLEMENTATION COMPLETE")
        self.stdout.write("=" * 80)

        self.stdout.write(
            f"  Active Grade 10 groups       : {len(groups)}"
        )
        self.stdout.write(
            f"  Subjects created             : {subjects_created}"
        )
        self.stdout.write(
            f"  Subjects reactivated         : {subjects_reactivated}"
        )
        self.stdout.write(
            f"  Requirements created         : {requirements_created}"
        )
        self.stdout.write(
            f"  Requirements corrected       : {requirements_corrected}"
        )
        self.stdout.write(
            f"  Requirements reactivated     : {requirements_reactivated}"
        )
        self.stdout.write(
            f"  Requirements deactivated     : {requirements_deactivated}"
        )
        self.stdout.write(
            f"  Requirements unchanged       : {requirements_unchanged}"
        )
        self.stdout.write(
            f"  Teacher assignments created  : {assignments_created}"
        )
        self.stdout.write(
            f"  Teacher assignments activated: {assignments_activated}"
        )
        self.stdout.write(
            f"  Teacher assignments disabled : {assignments_deactivated}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "AUTHORITATIVE GRADE 10 CURRICULUM IS CONSISTENT."
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "CRE authoritative teachers: T002, T006."
        )
        self.stdout.write(
            "CRE inactive teacher T007 is not an active assignment."
        )
        self.stdout.write(
            "ENG authoritative teachers: T011, T015."
        )
        self.stdout.write(
            "KIS authoritative teachers: T001, T020."
        )
        self.stdout.write(
            "EMCM authoritative teachers: T004, T013."
        )
        self.stdout.write(
            "French remains inactive until an active teacher exists."
        )
        self.stdout.write(
            "GST remains a 1/week Group Study / Life Skills requirement "
            "without an invented teacher."
        )
        self.stdout.write("")
        self.stdout.write(
            "No solver files were modified."
        )
        self.stdout.write(
            "No timetable entries were created or modified."
        )
        self.stdout.write(
            "No frontend files were modified."
        )
        self.stdout.write("=" * 80)
