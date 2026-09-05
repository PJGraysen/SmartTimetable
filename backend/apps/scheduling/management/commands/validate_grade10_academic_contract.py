from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.academics.models import InstructionalGroup, LessonRequirement

from apps.scheduling.engine.application.grade10_parallel_blocks import (
    GRADE10_PARALLEL_BLOCKS,
    validate_grade10_parallel_blocks,
)


CORE_REQUIREMENTS = {
    "ENG": 5,
    "KIS": 5,
    "EMCM": 5,
    "CRE": 4,
    "PE": 3,
    "CSL": 3,
    "ICT": 2,
    "PRP": 1,
}


PARALLEL_SUBJECTS = {
    subject
    for block in GRADE10_PARALLEL_BLOCKS
    for subject in block.subject_codes
}


class Command(BaseCommand):
    help = (
        "Read-only validation of the Grade 10 academic contract "
        "against current database requirements."
    )

    def subject_code(self, requirement):
        subject = getattr(requirement, "subject", None)

        if subject is not None:
            for field in (
                "code",
                "short_code",
                "abbreviation",
                "name",
            ):
                value = getattr(subject, field, None)
                if value not in (None, ""):
                    return str(value).upper()

        for field in (
            "subject_code",
            "subject_name",
            "code",
            "name",
        ):
            value = getattr(requirement, field, None)
            if value not in (None, ""):
                return str(value).upper()

        return "UNKNOWN"

    def lessons_per_week(self, requirement):
        return int(
            getattr(
                requirement,
                "lessons_per_week",
                0,
            )
            or 0
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 76)
        self.stdout.write(
            "SMARTTIMETABLE PRO - GRADE 10 ACADEMIC CONTRACT VALIDATION"
        )
        self.stdout.write("=" * 76)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        # Validate the authoritative application-level block definition
        # before comparing it with the database.
        validate_grade10_parallel_blocks()

        groups = tuple(
            InstructionalGroup.objects
            .filter(code__in=("10E", "10W"))
            .order_by("code")
        )

        if len(groups) != 2:
            self.stdout.write(
                f"FAIL - Expected Grade 10E and Grade 10W; found {len(groups)}."
            )
            return

        overall_failures = []

        # ------------------------------------------------------------------
        # AUTHORITATIVE PARALLEL BLOCKS
        # ------------------------------------------------------------------
        self.stdout.write("=== AUTHORITATIVE PARALLEL BLOCKS ===")

        for block in GRADE10_PARALLEL_BLOCKS:
            self.stdout.write(
                f"{block.code}: "
                f"{' / '.join(block.subject_codes)} "
                f"= {block.weekly_shared_slots} shared slots/week"
            )

        self.stdout.write("")

        # ------------------------------------------------------------------
        # GROUP VALIDATION
        # ------------------------------------------------------------------
        self.stdout.write("=== GROUP VALIDATION ===")

        for group in groups:
            code = str(group.code)

            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {code} | {group.name}"
            )

            requirements = tuple(
                LessonRequirement.objects
                .filter(
                    instructional_group=group,
                    is_active=True,
                )
                .select_related("subject")
            )

            by_subject = defaultdict(list)

            for requirement in requirements:
                by_subject[
                    self.subject_code(requirement)
                ].append(requirement)

            # --------------------------------------------------------------
            # Core requirements
            # --------------------------------------------------------------
            self.stdout.write("")
            self.stdout.write("CORE REQUIREMENTS:")

            for subject, expected in CORE_REQUIREMENTS.items():
                matches = by_subject.get(subject, [])

                if not matches:
                    message = (
                        f"FAIL - {code}: {subject} is missing "
                        f"(expected {expected}/week)"
                    )
                    self.stdout.write(message)
                    overall_failures.append(message)
                    continue

                actual = sum(
                    self.lessons_per_week(requirement)
                    for requirement in matches
                )

                if actual != expected:
                    message = (
                        f"FAIL - {code}: {subject} = {actual}/week; "
                        f"expected {expected}/week"
                    )
                    self.stdout.write(message)
                    overall_failures.append(message)
                else:
                    self.stdout.write(
                        f"PASS - {code}: {subject} = {actual}/week"
                    )

            # --------------------------------------------------------------
            # Parallel elective blocks
            # --------------------------------------------------------------
            self.stdout.write("")
            self.stdout.write("PARALLEL ELECTIVE BLOCKS:")

            for block in GRADE10_PARALLEL_BLOCKS:
                block_code = block.code
                expected_shared_slots = block.weekly_shared_slots

                self.stdout.write("")
                self.stdout.write(
                    f"  {block_code}: "
                    f"{' / '.join(block.subject_codes)} "
                    f"= {expected_shared_slots} shared slots/week"
                )

                block_ok = True

                for subject in block.subject_codes:
                    matches = by_subject.get(subject, [])

                    if not matches:
                        message = (
                            f"FAIL - {code}: {subject} missing "
                            f"from {block_code}"
                        )
                        self.stdout.write(f"    {message}")
                        overall_failures.append(message)
                        block_ok = False
                        continue

                    actual = sum(
                        self.lessons_per_week(requirement)
                        for requirement in matches
                    )

                    if actual != expected_shared_slots:
                        message = (
                            f"FAIL - {code}: {subject} = {actual}/week; "
                            f"expected {expected_shared_slots}/week "
                            f"for {block_code}"
                        )
                        self.stdout.write(f"    {message}")
                        overall_failures.append(message)
                        block_ok = False
                    else:
                        self.stdout.write(
                            f"    PASS - {subject} = {actual}/week"
                        )

                if block_ok:
                    self.stdout.write(
                        f"    PASS - {block_code}: all subjects present "
                        f"at required weekly frequency"
                    )

            # --------------------------------------------------------------
            # Standalone Music protection
            #
            # MUS is part of OPTION_1. This validator therefore verifies
            # its presence and frequency as a block subject. It does not
            # treat MUS as an independent standalone requirement.
            # --------------------------------------------------------------
            music_requirements = by_subject.get("MUS", [])

            if music_requirements:
                music_total = sum(
                    self.lessons_per_week(requirement)
                    for requirement in music_requirements
                )

                option_1 = next(
                    (
                        block
                        for block in GRADE10_PARALLEL_BLOCKS
                        if block.code == "OPTION_1"
                    ),
                    None,
                )

                expected_music = (
                    option_1.weekly_shared_slots
                    if option_1 is not None
                    else 5
                )

                if music_total == expected_music:
                    self.stdout.write(
                        "    PASS - MUS is represented only through "
                        "the OPTION_1 elective block requirement."
                    )
                else:
                    message = (
                        f"FAIL - {code}: MUS = {music_total}/week; "
                        f"expected {expected_music}/week as OPTION_1"
                    )
                    self.stdout.write(f"    {message}")
                    overall_failures.append(message)

            # --------------------------------------------------------------
            # Unexpected parallel-subject protection
            # --------------------------------------------------------------
            unexpected_parallel_subjects = sorted(
                subject
                for subject in by_subject
                if subject in PARALLEL_SUBJECTS
                and subject not in {
                    subject_code
                    for block in GRADE10_PARALLEL_BLOCKS
                    for subject_code in block.subject_codes
                }
            )

            if unexpected_parallel_subjects:
                for subject in unexpected_parallel_subjects:
                    message = (
                        f"FAIL - {code}: {subject} is not represented "
                        f"by an authoritative Grade 10 parallel block"
                    )
                    self.stdout.write(f"    {message}")
                    overall_failures.append(message)

            # --------------------------------------------------------------
            # Requirement count
            # --------------------------------------------------------------
            self.stdout.write("")
            self.stdout.write(
                f"ACTIVE REQUIREMENT ROWS: {len(requirements)}"
            )

        # ------------------------------------------------------------------
        # FINAL RESULT
        # ------------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("=" * 76)

        if overall_failures:
            self.stdout.write(
                "GRADE 10 ACADEMIC CONTRACT VALIDATION: FAIL"
            )
            self.stdout.write("")
            self.stdout.write("AUTHORITATIVE MISMATCHES:")

            for failure in overall_failures:
                self.stdout.write(f"  {failure}")

            self.stdout.write("")
            self.stdout.write("NO DATABASE CHANGES WERE MADE.")
            self.stdout.write("NO SOLVER CHANGES WERE MADE.")
            self.stdout.write("=" * 76)
            return

        self.stdout.write(
            "GRADE 10 ACADEMIC CONTRACT VALIDATION: PASS"
        )
        self.stdout.write(
            "All authoritative requirements are represented."
        )
        self.stdout.write("NO DATABASE CHANGES WERE MADE.")
        self.stdout.write("=" * 76)
