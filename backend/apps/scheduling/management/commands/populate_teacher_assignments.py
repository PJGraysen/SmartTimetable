from django.core.management.base import BaseCommand
from django.db import transaction

from apps.scheduling.models import (
    Teacher,
    LessonRequirement,
    TeacherAssignment,
)


class Command(BaseCommand):
    help = (
        "Populate the authoritative Senior School teacher-assignment "
        "contract while preserving existing assignments. "
        "Grade 10 assignments are preserved."
    )

    # Existing production mappings.
    UNAMBIGUOUS_ASSIGNMENTS = {
        "Physical Education": "T014",
        "ICT Skills": "T014",
        "Community Service Learning": "T016",
    }

    # ------------------------------------------------------------
    # AUTHORITATIVE SENIOR SCHOOL TEACHER CONTRACT
    # ------------------------------------------------------------
    #
    # Each tuple is:
    #
    #     group -> subject -> eligible teacher codes
    #
    # This is deliberately explicit and group-scoped.
    #
    # PPI:
    #     T001 for ALL 3E, 3W, 4E, 4W.
    #
    # Multi-teacher entries are preserved because the production
    # TeacherAssignment model permits multiple eligible teachers
    # for a LessonRequirement.
    #
    SENIOR_TEACHER_CONTRACT = {
        "3E": {
            "PPI": {"T001"},
            "CRE": {"T006"},
            "MAT": {"T004"},
            "CHEM": {"T005"},
            "HIS": {"T006"},
            "AGR": {"T008", "T010"},
            "BIO": {"T008", "T016"},
            "PHY": {"T013"},
            "ENG": {"T015"},
            "KIS": {"T017"},
            "BUS": {"T012"},
            "CS": {"T019"},
            "CSL": {"T016"},
            "PE": {"T014"},
        },
        "3W": {
            "PPI": {"T001"},
            "CRE": {"T006"},
            "MAT": {"T012"},
            "CHEM": {"T005", "T016"},
            "HIS": {"T006"},
            "AGR": {"T008", "T010"},
            "BIO": {"T008"},
            "PHY": {"T013"},
            "ENG": {"T011"},
            "KIS": {"T018"},
            "BUS": {"T012"},
            "CS": {"T019"},
            "CSL": {"T016"},
            "PE": {"T014"},
        },
        "4E": {
            "PPI": {"T001"},
            "CRE": {"T006", "T007"},
            "MAT": {"T012"},
            "CHEM": {"T009"},
            "HIS": {"T007"},
            "AGR": {"T010"},
            "BIO": {"T010"},
            "PHY": {"T005"},
            "ENG": {"T015"},
            "KIS": {"T018"},
            "BUS": {"T019"},
            "CS": {"T019"},
            "CSL": {"T016"},
            "PE": {"T014"},
        },
        "4W": {
            "PPI": {"T001"},
            "CRE": {"T007"},
            "MAT": {"T012"},
            "CHEM": {"T009"},
            "HIS": {"T007"},
            "AGR": {"T010"},
            "BIO": {"T010"},
            "PHY": {"T005"},
            "ENG": {"T015"},
            "KIS": {"T017", "T018"},
            "BUS": {"T019"},
            "CS": {"T019"},
            "CSL": {"T016"},
            "PE": {"T014"},
        },
    }

    SUBJECT_CODE_BY_NAME = {
        "Pastoral Programme and Instruction": "PPI",
        "Pastoral/Religious Programme": "PPI",
        "Christian Religious Education": "CRE",
        "Mathematics": "MAT",
        "Chemistry": "CHEM",
        "History": "HIS",
        "Agriculture": "AGR",
        "Biology": "BIO",
        "Physics": "PHY",
        "English": "ENG",
        "Kiswahili": "KIS",
        "Business Studies": "BUS",
        "Computer Science": "CS",
        "Computer Studies": "CS",
        "Community Service Learning": "CSL",
        "Physical Education": "PE",
    }

    GROUP_NAME_TO_CODE = {
        "Form 3E": "3E",
        "Form 3W": "3W",
        "Form 4E": "4E",
        "Form 4W": "4W",
    }

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.WARNING(
                "\n=== SMART TIMETABLE SENIOR SCHOOL TEACHER "
                "ASSIGNMENT SAFETY CHECK ==="
            )
        )

        # --------------------------------------------------------
        # 1. Teacher-code integrity.
        # --------------------------------------------------------
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
            raise RuntimeError(
                "Teacher-code integrity failure. "
                f"Expected={sorted(expected_codes)} "
                f"Actual={sorted(actual_codes)}"
            )

        for code, teacher in teachers.items():
            expected_number = int(code[1:])

            if teacher.teacher_number != expected_number:
                raise RuntimeError(
                    f"{code} has teacher_number="
                    f"{teacher.teacher_number}; "
                    f"expected {expected_number}."
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Teacher-code integrity verified: T001-T020."
            )
        )

        # --------------------------------------------------------
        # 2. Validate every contract teacher exists.
        # --------------------------------------------------------
        contract_teacher_codes = set()

        for group_code, subjects in self.SENIOR_TEACHER_CONTRACT.items():
            for subject_code, teacher_codes in subjects.items():
                contract_teacher_codes.update(teacher_codes)

        missing_contract_teachers = sorted(
            contract_teacher_codes - set(teachers.keys())
        )

        if missing_contract_teachers:
            raise RuntimeError(
                "Contract references missing teachers: "
                f"{missing_contract_teachers}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "All Senior School contract teachers exist."
            )
        )

        # --------------------------------------------------------
        # 3. Load exact active Senior School requirements.
        # --------------------------------------------------------
        requirements = list(
            LessonRequirement.objects
            .select_related(
                "subject",
                "instructional_group",
                "term",
            )
            .filter(is_active=True)
            .order_by(
                "instructional_group__name",
                "subject__name",
                "lessons_per_week",
            )
        )

        senior_requirements = []

        for requirement in requirements:

            group_name = requirement.instructional_group.name.strip()

            if group_name not in self.GROUP_NAME_TO_CODE:
                continue

            senior_requirements.append(requirement)

        self.stdout.write(
            f"Active Senior School requirements: "
            f"{len(senior_requirements)}"
        )

        # --------------------------------------------------------
        # 4. Build requirement lookup by group + subject code.
        #
        # Multiple LessonRequirement rows for the same subject are
        # intentional in the Senior School curriculum because the
        # production materializer represents standalone/block/
        # practical components separately.
        # --------------------------------------------------------
        requirement_map = {}

        for requirement in senior_requirements:

            group_name = requirement.instructional_group.name.strip()
            group_code = self.GROUP_NAME_TO_CODE[group_name]

            subject_name = requirement.subject.name.strip()
            subject_code = self.SUBJECT_CODE_BY_NAME.get(subject_name)

            if subject_code is None:
                continue

            key = (
                group_code,
                subject_code,
            )

            requirement_map.setdefault(
                key,
                [],
            ).append(requirement)

        # --------------------------------------------------------
        # 5. Existing assignment set.
        # --------------------------------------------------------
        existing = set(
            TeacherAssignment.objects.values_list(
                "teacher_id",
                "lesson_requirement_id",
            )
        )

        before_count = len(existing)

        self.stdout.write(
            f"Existing TeacherAssignment rows: {before_count}"
        )

        # --------------------------------------------------------
        # 6. Validate that every Senior contract pair has at least
        #    one corresponding active LessonRequirement.
        # --------------------------------------------------------
        missing_requirements = []

        for group_code, subjects in self.SENIOR_TEACHER_CONTRACT.items():

            for subject_code in subjects:

                key = (
                    group_code,
                    subject_code,
                )

                if key not in requirement_map:
                    missing_requirements.append(
                        (
                            group_code,
                            subject_code,
                        )
                    )

        if missing_requirements:
            raise RuntimeError(
                "Senior School teacher contract references "
                "missing active LessonRequirements: "
                f"{missing_requirements}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "All Senior School teacher-contract subjects "
                "have active LessonRequirements."
            )
        )

        # --------------------------------------------------------
        # 7. Create missing assignments.
        # --------------------------------------------------------
        created = 0
        already_present = 0

        created_by_group = {
            group_code: 0
            for group_code in self.SENIOR_TEACHER_CONTRACT
        }

        with transaction.atomic():

            # ----------------------------------------------------
            # Senior School contract.
            # ----------------------------------------------------
            for group_code, subjects in self.SENIOR_TEACHER_CONTRACT.items():

                for subject_code, teacher_codes in subjects.items():

                    requirements_for_subject = requirement_map[
                        (
                            group_code,
                            subject_code,
                        )
                    ]

                    for requirement in requirements_for_subject:

                        for teacher_code in sorted(teacher_codes):

                            teacher = teachers[teacher_code]

                            pair = (
                                teacher.pk,
                                requirement.pk,
                            )

                            if pair in existing:
                                already_present += 1

                                self.stdout.write(
                                    f"EXISTS | "
                                    f"{teacher_code} | "
                                    f"{requirement.instructional_group.name} | "
                                    f"{requirement.subject.name} | "
                                    f"{requirement.lessons_per_week}/week"
                                )

                                continue

                            TeacherAssignment.objects.create(
                                teacher=teacher,
                                lesson_requirement=requirement,
                            )

                            existing.add(pair)
                            created += 1
                            created_by_group[group_code] += 1

                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"CREATED | "
                                    f"{teacher_code} | "
                                    f"{requirement.instructional_group.name} | "
                                    f"{requirement.subject.name} | "
                                    f"{requirement.lessons_per_week}/week"
                                )
                            )

        # --------------------------------------------------------
        # 8. Exact post-write contract verification.
        # --------------------------------------------------------
        self.stdout.write(
            "\n=== SENIOR SCHOOL POST-WRITE CONTRACT VERIFICATION ==="
        )

        verification_failures = []

        for group_code, subjects in self.SENIOR_TEACHER_CONTRACT.items():

            group_name = next(
                name
                for name, code in self.GROUP_NAME_TO_CODE.items()
                if code == group_code
            )

            for subject_code, expected_teacher_codes in subjects.items():

                requirements_for_subject = requirement_map[
                    (
                        group_code,
                        subject_code,
                    )
                ]

                for requirement in requirements_for_subject:

                    actual_teacher_codes = set(
                        TeacherAssignment.objects
                        .filter(
                            lesson_requirement=requirement,
                            is_active=True,
                        )
                        .select_related("teacher")
                        .values_list(
                            "teacher__employee_code",
                            flat=True,
                        )
                    )

                    expected = set(expected_teacher_codes)

                    if actual_teacher_codes != expected:
                        verification_failures.append(
                            (
                                group_code,
                                subject_code,
                                requirement.pk,
                                expected,
                                actual_teacher_codes,
                            )
                        )

                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"PASS | "
                                f"{group_code} | "
                                f"{subject_code} | "
                                f"{requirement.lessons_per_week}/week | "
                                f"T={sorted(actual_teacher_codes)}"
                            )
                        )

        if verification_failures:
            self.stdout.write(
                self.style.ERROR(
                    "\nCONTRACT VERIFICATION FAILURES:"
                )
            )

            for (
                group_code,
                subject_code,
                requirement_id,
                expected,
                actual,
            ) in verification_failures:

                self.stdout.write(
                    self.style.ERROR(
                        f"FAIL | "
                        f"{group_code} | "
                        f"{subject_code} | "
                        f"requirement={requirement_id} | "
                        f"EXPECTED={sorted(expected)} | "
                        f"ACTUAL={sorted(actual)}"
                    )
                )

            raise RuntimeError(
                "Senior School teacher contract verification failed."
            )

        # --------------------------------------------------------
        # 9. Explicit PPI verification.
        # --------------------------------------------------------
        self.stdout.write(
            "\n=== PPI FINAL VERIFICATION ==="
        )

        ppi_failures = []

        for group_name in (
            "Form 3E",
            "Form 3W",
            "Form 4E",
            "Form 4W",
        ):

            group_code = self.GROUP_NAME_TO_CODE[group_name]

            ppi_requirements = requirement_map.get(
                (
                    group_code,
                    "PPI",
                ),
                [],
            )

            if len(ppi_requirements) != 1:
                ppi_failures.append(
                    (
                        group_code,
                        "expected exactly one PPI requirement",
                        len(ppi_requirements),
                    )
                )
                continue

            requirement = ppi_requirements[0]

            actual_teacher_codes = set(
                TeacherAssignment.objects
                .filter(
                    lesson_requirement=requirement,
                    is_active=True,
                )
                .select_related("teacher")
                .values_list(
                    "teacher__employee_code",
                    flat=True,
                )
            )

            if actual_teacher_codes != {"T001"}:
                ppi_failures.append(
                    (
                        group_code,
                        "expected T001",
                        actual_teacher_codes,
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{group_code}: PPI -> T001 PASS"
                    )
                )

        if ppi_failures:
            raise RuntimeError(
                f"PPI verification failure: {ppi_failures}"
            )

        # --------------------------------------------------------
        # 10. Final report.
        # --------------------------------------------------------
        final_count = TeacherAssignment.objects.count()

        self.stdout.write("")
        self.stdout.write("=" * 68)
        self.stdout.write("V47 FINAL RESULT")
        self.stdout.write("=" * 68)

        self.stdout.write(
            f"TeacherAssignment rows before: {before_count}"
        )

        self.stdout.write(
            f"TeacherAssignment rows after:  {final_count}"
        )

        self.stdout.write(
            f"Created by V47:                {created}"
        )

        self.stdout.write(
            f"Already present:               {already_present}"
        )

        self.stdout.write("")
        self.stdout.write("Created by Senior School group:")

        for group_code, count in created_by_group.items():
            self.stdout.write(
                f"  {group_code}: {count}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Senior School teacher contract: PASS"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "PPI contract: PASS"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Existing TeacherAssignment rows were preserved."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Teacher codes were not changed."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Solver was NOT invoked."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "V47 COMPLETE."
            )
        )


if __name__ == "__main__":
    pass