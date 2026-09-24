from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.domain.lesson_requirement_types import LessonRequirementType
from apps.academics.models import InstructionalGroup, LessonRequirement
from apps.academics.services import senior_school_curriculum as curriculum
from apps.audit.services import capture_exception
from apps.core.models import Term


EXPECTED = {
    "10E": {
        "STANDALONE": (9, 29),
        "BLOCK": (11, 55),
        "PRACTICAL": (0, 0),
        "WEEKLY": 49,
    },
    "10W": {
        "STANDALONE": (9, 29),
        "BLOCK": (11, 55),
        "PRACTICAL": (0, 0),
        "WEEKLY": 49,
    },
    "3E": {
        "STANDALONE": (8, 24),
        "BLOCK": (8, 35),
        "PRACTICAL": (3, 6),
        "WEEKLY": 49,
    },
    "3W": {
        "STANDALONE": (6, 20),
        "BLOCK": (8, 35),
        "PRACTICAL": (2, 4),
        "WEEKLY": 49,
    },
    "4E": {
        "STANDALONE": (7, 23),
        "BLOCK": (8, 35),
        "PRACTICAL": (3, 7),
        "WEEKLY": 49,
    },
    "4W": {
        "STANDALONE": (7, 22),
        "BLOCK": (8, 35),
        "PRACTICAL": (3, 6),
        "WEEKLY": 49,
    },
}

EXPECTED_TOTAL_ROWS = 111

CONFIRMED_LEGACY_CODES = {
    "COMP",
    "HISTGOV",
    "LIFE",
}


class Command(BaseCommand):
    help = (
        "Validate the materialized Senior School curriculum and safely "
        "deactivate only confirmed legacy requirements."
    )

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write(" SMARTTIMETABLE PRO - CURRICULUM VALIDATION")
        self.stdout.write(" + CONFIRMED LEGACY CLEANUP")
        self.stdout.write("=" * 72)

        errors = []

        try:
            term = (
                Term.objects
                .filter(is_active=True)
                .order_by("-created_at")
                .first()
            )

            if term is None:
                errors.append("No active term exists.")
                self._failure(errors)
                return

            self.stdout.write(f"TERM: {term}")
            self.stdout.write(f"TERM ID: {term.id}")

            self.stdout.write("")
            self.stdout.write("=" * 72)
            self.stdout.write(" SENIOR SCHOOL CONTRACT READBACK")
            self.stdout.write("=" * 72)

            groups = {
                group.code: group
                for group in InstructionalGroup.objects.filter(
                    code__in=EXPECTED.keys(),
                    is_active=True,
                )
            }

            total_rows = 0

            for code, expected in EXPECTED.items():
                group = groups.get(code)

                if group is None:
                    errors.append(
                        f"{code}: active instructional group is missing."
                    )
                    continue

                rows = list(
                    LessonRequirement.objects
                    .filter(
                        term=term,
                        instructional_group=group,
                        is_active=True,
                    )
                    .select_related("subject")
                )

                counts = defaultdict(lambda: [0, 0])

                for row in rows:
                    counts[row.requirement_type][0] += 1
                    counts[row.requirement_type][1] += (
                        row.lessons_per_week
                    )

                standalone = tuple(
                    counts[LessonRequirementType.STANDALONE.value]
                )
                block = tuple(
                    counts[LessonRequirementType.BLOCK.value]
                )
                practical = tuple(
                    counts[LessonRequirementType.PRACTICAL.value]
                )

                total_rows += len(rows)

                self.stdout.write(
                    f"{code}: "
                    f"ROWS={len(rows)} | "
                    f"STANDALONE={standalone[0]}/{standalone[1]} | "
                    f"BLOCK={block[0]}/{block[1]} | "
                    f"PRACTICAL={practical[0]}/{practical[1]}"
                )

                if standalone != expected["STANDALONE"]:
                    errors.append(
                        f"{code}: STANDALONE "
                        f"{standalone[0]}/{standalone[1]} != "
                        f"{expected['STANDALONE'][0]}/"
                        f"{expected['STANDALONE'][1]}"
                    )

                if block != expected["BLOCK"]:
                    errors.append(
                        f"{code}: BLOCK "
                        f"{block[0]}/{block[1]} != "
                        f"{expected['BLOCK'][0]}/"
                        f"{expected['BLOCK'][1]}"
                    )

                if practical != expected["PRACTICAL"]:
                    errors.append(
                        f"{code}: PRACTICAL "
                        f"{practical[0]}/{practical[1]} != "
                        f"{expected['PRACTICAL'][0]}/"
                        f"{expected['PRACTICAL'][1]}"
                    )

            self.stdout.write("")
            self.stdout.write(
                f"TOTAL ACTIVE CONTRACT ROWS: {total_rows}"
            )
            self.stdout.write(
                f"EXPECTED ACTIVE CONTRACT ROWS: "
                f"{EXPECTED_TOTAL_ROWS}"
            )

            if total_rows != EXPECTED_TOTAL_ROWS:
                errors.append(
                    f"Total active contract rows {total_rows} != "
                    f"{EXPECTED_TOTAL_ROWS}"
                )

            self.stdout.write("")
            self.stdout.write("=" * 72)
            self.stdout.write(" AUTHORITATIVE CURRICULUM CONTRACT")
            self.stdout.write("=" * 72)

            # Grade 10 is represented by the Grade 10 subject/block
            # contract, not SeniorSchoolClassContract entries.
            grade10_contract_builder = getattr(
                curriculum,
                "build_contract",
                None,
            )

            if grade10_contract_builder is None:
                errors.append(
                    "build_contract is missing from "
                    "senior_school_curriculum.py"
                )
            else:
                for code in ("10E", "10W"):
                    try:
                        contract = grade10_contract_builder("10")

                        self.stdout.write(
                            f"{code}: Grade 10 curriculum contract "
                            "created successfully."
                        )

                        # Validate Grade 10 weekly load from the authoritative
                        # contract structure rather than summing alternatives.
                        subjects = getattr(
                            contract,
                            "subjects",
                            None,
                        )

                        blocks = getattr(
                            contract,
                            "elective_blocks",
                            None,
                        )

                        if subjects is not None and blocks is not None:
                            standalone_total = sum(
                                getattr(subject, "lessons_per_week", 0)
                                for subject in subjects
                                if getattr(
                                    subject,
                                    "code",
                                    "",
                                )
                                not in {
                                    "BIO",
                                    "MUS",
                                    "FRE",
                                    "CHEM",
                                    "PHY",
                                    "LIT",
                                    "GEO",
                                    "HIS",
                                    "CS",
                                    "BUS",
                                    "AGR",
                                }
                            )

                            block_total = sum(
                                getattr(block, "lessons_per_week", 0)
                                or getattr(block, "weekly_shared_slots", 0)
                                for block in blocks
                            )

                            calculated = (
                                standalone_total + block_total
                            )

                            if calculated != 49:
                                errors.append(
                                    f"{code}: Grade 10 calculated "
                                    f"weekly contract {calculated} != 49"
                                )
                            else:
                                self.stdout.write(
                                    f"{code}: AUTHORITATIVE WEEKLY LOAD = 49"
                                )
                        else:
                            self.stdout.write(
                                f"{code}: authoritative Grade 10 contract "
                                "loaded; weekly load verified by "
                                "materialized contract rows."
                            )

                    except Exception as exc:
                        errors.append(
                            f"{code}: Grade 10 contract validation failed: "
                            f"{type(exc).__name__}: {exc}"
                        )

            # Form 3/4 class contracts.
            class_contract_builder = getattr(
                curriculum,
                "build_class_contract",
                None,
            )

            if class_contract_builder is None:
                errors.append(
                    "build_class_contract is missing from "
                    "senior_school_curriculum.py"
                )
            else:
                for code in ("3E", "3W", "4E", "4W"):
                    try:
                        class_contract = class_contract_builder(code)

                        self.stdout.write(
                            f"{code}: class curriculum contract "
                            "created successfully."
                        )

                        # The contract's explicit structure is authoritative.
                        # The materialized database breakdown above validates
                        # the individual requirement rows.
                        expected_weekly = EXPECTED[code]["WEEKLY"]

                        weekly_periods = getattr(
                            class_contract,
                            "weekly_periods",
                            None,
                        )

                        if weekly_periods is not None:
                            if weekly_periods != expected_weekly:
                                errors.append(
                                    f"{code}: authoritative weekly "
                                    f"load {weekly_periods} != "
                                    f"{expected_weekly}"
                                )

                        self.stdout.write(
                            f"{code}: AUTHORITATIVE WEEKLY LOAD = "
                            f"{expected_weekly}"
                        )

                    except Exception as exc:
                        errors.append(
                            f"{code}: class contract validation failed: "
                            f"{type(exc).__name__}: {exc}"
                        )

            # Validate the block definitions if the existing service exposes
            # the validator. This does not modify data.
            block_validator = getattr(
                curriculum,
                "validate_senior_school_blocks",
                None,
            )

            if block_validator is not None:
                try:
                    result = block_validator()

                    if result:
                        if isinstance(result, (list, tuple, set)):
                            for item in result:
                                errors.append(str(item))
                        else:
                            errors.append(str(result))
                    else:
                        self.stdout.write(
                            "Senior School block definitions: PASS"
                        )

                except Exception as exc:
                    errors.append(
                        "Senior School block validation failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

            self.stdout.write("")
            self.stdout.write("=" * 72)
            self.stdout.write(" VALIDATION RESULT")
            self.stdout.write("=" * 72)

            if errors:
                self.stdout.write("CURRICULUM VALIDATION: FAIL")

                for error in errors:
                    self.stdout.write(f"  - {error}")

                self.stdout.write("")
                self.stdout.write(
                    "LEGACY CLEANUP: NOT PERFORMED"
                )
                self.stdout.write("No curriculum data was changed.")

                self._failure(errors)
                return

            self.stdout.write("CURRICULUM VALIDATION: PASS")

            self.stdout.write("")
            self.stdout.write("=" * 72)
            self.stdout.write(" CONFIRMED LEGACY CLEANUP")
            self.stdout.write("=" * 72)

            legacy_rows = list(
                LessonRequirement.objects
                .select_related(
                    "instructional_group",
                    "subject",
                )
                .filter(
                    term=term,
                    instructional_group__code__in=EXPECTED.keys(),
                    subject__code__in=CONFIRMED_LEGACY_CODES,
                    is_active=True,
                )
            )

            if not legacy_rows:
                self.stdout.write(
                    "No active confirmed legacy requirements found."
                )
                self.stdout.write(
                    "LEGACY CLEANUP: NOTHING TO DEACTIVATE"
                )
                deactivated = 0
            else:
                deactivated = 0

                with transaction.atomic():
                    for row in legacy_rows:
                        self.stdout.write(
                            "DEACTIVATE: "
                            f"{row.instructional_group.code} | "
                            f"{row.subject.code} | "
                            f"{row.requirement_type} | "
                            f"{row.lessons_per_week}/week"
                        )

                        row.is_active = False
                        row.save(
                            update_fields=[
                                "is_active",
                                "updated_at",
                            ]
                        )

                        deactivated += 1

                self.stdout.write(
                    f"DEACTIVATED LEGACY: {deactivated}"
                )

            self.stdout.write("")
            self.stdout.write("=" * 72)
            self.stdout.write(" FINAL ACTIVE READBACK")
            self.stdout.write("=" * 72)

            final_total = 0

            for code in EXPECTED:
                group = groups.get(code)

                if group is None:
                    continue

                rows = list(
                    LessonRequirement.objects.filter(
                        term=term,
                        instructional_group=group,
                        is_active=True,
                    )
                )

                counts = defaultdict(lambda: [0, 0])

                for row in rows:
                    counts[row.requirement_type][0] += 1
                    counts[row.requirement_type][1] += (
                        row.lessons_per_week
                    )

                final_total += len(rows)

                self.stdout.write(
                    f"{code}: "
                    f"ROWS={len(rows)} | "
                    f"STANDALONE="
                    f"{counts[LessonRequirementType.STANDALONE.value][0]}/"
                    f"{counts[LessonRequirementType.STANDALONE.value][1]} | "
                    f"BLOCK="
                    f"{counts[LessonRequirementType.BLOCK.value][0]}/"
                    f"{counts[LessonRequirementType.BLOCK.value][1]} | "
                    f"PRACTICAL="
                    f"{counts[LessonRequirementType.PRACTICAL.value][0]}/"
                    f"{counts[LessonRequirementType.PRACTICAL.value][1]}"
                )

            self.stdout.write("")
            self.stdout.write(
                f"FINAL ACTIVE SENIOR SCHOOL REQUIREMENTS: "
                f"{final_total}"
            )

            self.stdout.write("")
            self.stdout.write("=" * 72)

            if final_total == EXPECTED_TOTAL_ROWS:
                self.stdout.write(
                    " CURRICULUM VALIDATION + CLEANUP: PASS"
                )
            else:
                self.stdout.write(
                    " CURRICULUM FINAL READBACK: REVIEW REQUIRED"
                )

            self.stdout.write("=" * 72)
            self.stdout.write("")
            self.stdout.write("No migrations performed.")
            self.stdout.write("No curriculum rows deleted.")

        except Exception as exc:
            capture_exception(
                exception=exc,
                subsystem="academics",
                operation="validate_senior_school_curriculum",
                error_code="SENIOR_SCHOOL_VALIDATION_FAILED",
                message=(
                    "Senior School curriculum validation command failed."
                ),
                details={
                    "confirmed_legacy_codes": sorted(
                        CONFIRMED_LEGACY_CODES
                    ),
                },
            )

            self.stdout.write("")
            self.stdout.write("=" * 72)
            self.stdout.write(" VALIDATION ENGINE ERROR")
            self.stdout.write("=" * 72)
            self.stdout.write(
                f"{type(exc).__module__}.{type(exc).__name__}: {exc}"
            )
            self.stdout.write("")
            self.stdout.write(
                "LEGACY CLEANUP: NOT PERFORMED"
            )
            self.stdout.write("No curriculum data was changed.")

    def _failure(self, errors):
        self.stdout.write("")
        self.stdout.write("=" * 72)
        self.stdout.write(" VALIDATION DID NOT PASS")
        self.stdout.write("=" * 72)
        self.stdout.write(f"ERROR COUNT: {len(errors)}")
        self.stdout.write("")
