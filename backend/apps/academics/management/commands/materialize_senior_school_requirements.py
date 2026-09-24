from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.domain.lesson_requirement_types import (
    LessonRequirementType,
)
from apps.academics.models import (
    InstructionalGroup,
    LessonRequirement,
    Subject,
)
from apps.academics.services.senior_school_curriculum import (
    EXPECTED_SENIOR_SCHOOL_GROUP_CODES,
    GRADE10_GROUP_CODES,
    SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS,
    build_contract,
)
from apps.audit.services import capture_exception
from apps.core.models import Term


GRADE10_BLOCK_SUBJECTS = {
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


FORM_PRACTICALS = {
    "3E": {
        "CHEM": 2,
        "BIO": 2,
        "PHY": 2,
    },
    "3W": {
        "BIO": 2,
        "CS": 2,
    },
    "4E": {
        "CHEM": 3,
        "BIO": 2,
        "PHY": 2,
    },
    "4W": {
        "BIO": 2,
        "PHY": 2,
        "CS": 2,
    },
}


def get_subjects():
    return {
        subject.code: subject
        for subject in Subject.objects.all()
    }


def get_active_term():
    return (
        Term.objects
        .select_related("academic_year")
        .filter(is_active=True)
        .order_by("-start_date", "-created_at")
        .first()
    )


def get_instructional_group(code: str):
    """
    Resolve the established Senior School instructional group.

    Actual hierarchy:

        InstructionalGroup
            -> TeachingGroup
                -> Stream
                    -> Grade

    Therefore the valid select_related path is
    teaching_group__stream__grade.
    """

    return (
        InstructionalGroup.objects
        .select_related(
            "teaching_group",
            "teaching_group__stream",
            "teaching_group__stream__grade",
        )
        .filter(
            code=code,
            is_active=True,
        )
        .first()
    )


def require_subject(subjects, code: str):
    subject = subjects.get(code)

    if subject is None:
        raise ValueError(
            f"Required Senior School subject '{code}' does not exist."
        )

    return subject


def get_subject_contract_code(item):
    return getattr(item, "code", None)


def get_subject_contract_weekly(item):
    value = getattr(item, "lessons_per_week", None)

    if value is None:
        value = getattr(item, "weekly_lessons", None)

    return value


def get_block_weekly(block):
    value = getattr(block, "lessons_per_week", None)

    if value is None:
        value = getattr(block, "weekly_shared_slots", None)

    if value is None:
        raise ValueError(
            f"Parallel block '{block}' has no weekly lesson value."
        )

    return int(value)


def build_grade10_rows(subjects):
    contract = build_contract("GRADE10")

    rows = []

    for subject_contract in contract.subjects:
        code = get_subject_contract_code(subject_contract)
        weekly = get_subject_contract_weekly(subject_contract)

        if not code or weekly is None:
            raise ValueError(
                f"Invalid Grade 10 subject contract entry: "
                f"{subject_contract!r}"
            )

        requirement_type = (
            LessonRequirementType.BLOCK
            if code in GRADE10_BLOCK_SUBJECTS
            else LessonRequirementType.STANDALONE
        )

        rows.append(
            (
                require_subject(subjects, code),
                int(weekly),
                requirement_type,
            )
        )

    return rows


def build_form_rows(group_code, subjects):
    contract = SENIOR_SCHOOL_CLASS_CURRICULUM_CONTRACTS.get(
        group_code
    )

    if contract is None:
        raise ValueError(
            f"No Senior School curriculum contract exists for "
            f"'{group_code}'."
        )

    rows = []

    for subject_contract in contract.standalone_subjects:
        code = get_subject_contract_code(subject_contract)
        weekly = get_subject_contract_weekly(subject_contract)

        if not code or weekly is None:
            raise ValueError(
                f"Invalid {group_code} standalone subject contract "
                f"entry: {subject_contract!r}"
            )

        rows.append(
            (
                require_subject(subjects, code),
                int(weekly),
                LessonRequirementType.STANDALONE,
            )
        )

    for block in contract.parallel_blocks:
        weekly = get_block_weekly(block)

        for code in block.subject_codes:
            rows.append(
                (
                    require_subject(subjects, code),
                    weekly,
                    LessonRequirementType.BLOCK,
                )
            )

    for code, weekly in FORM_PRACTICALS.get(
        group_code,
        {},
    ).items():
        rows.append(
            (
                require_subject(subjects, code),
                int(weekly),
                LessonRequirementType.PRACTICAL,
            )
        )

    return rows


def validate_generated_rows(definitions):
    seen = set()

    for group_code, rows in definitions.items():
        for subject, weekly, requirement_type in rows:

            if weekly < 1:
                raise ValueError(
                    f"Invalid weekly lesson count: "
                    f"{group_code} / {subject.code} / "
                    f"{requirement_type} / {weekly}"
                )

            key = (
                group_code,
                subject.code,
                requirement_type,
            )

            if key in seen:
                raise ValueError(
                    "Duplicate requirement generated: "
                    f"{group_code} / {subject.code} / "
                    f"{requirement_type}"
                )

            seen.add(key)


class Command(BaseCommand):
    help = (
        "Materialize Grade 10, Form 3 and Form 4 "
        "LessonRequirement records."
    )

    def handle(self, *args, **options):

        operation = (
            "materialize_senior_school_lesson_requirements"
        )

        try:

            term = get_active_term()

            if term is None:
                raise ValueError(
                    "No active academic term exists."
                )

            subjects = get_subjects()

            groups = {}

            missing_groups = []

            for code in EXPECTED_SENIOR_SCHOOL_GROUP_CODES:
                group = get_instructional_group(code)

                if group is None:
                    missing_groups.append(code)
                else:
                    groups[code] = group

            if missing_groups:
                raise ValueError(
                    "Missing active Senior School instructional "
                    "groups: "
                    + ", ".join(missing_groups)
                )

            definitions = {}

            for group_code in GRADE10_GROUP_CODES:
                definitions[group_code] = (
                    build_grade10_rows(subjects)
                )

            for group_code in (
                "3E",
                "3W",
                "4E",
                "4W",
            ):
                definitions[group_code] = build_form_rows(
                    group_code,
                    subjects,
                )

            validate_generated_rows(definitions)

            expected_counts = {
                group_code: len(rows)
                for group_code, rows in definitions.items()
            }

            created = 0
            updated = 0
            deactivated_legacy = 0

            with transaction.atomic():

                for group_code, rows in definitions.items():

                    group = groups[group_code]

                    for (
                        subject,
                        weekly,
                        requirement_type,
                    ) in rows:

                        requirement, was_created = (
                            LessonRequirement.objects
                            .select_for_update()
                            .get_or_create(
                                term=term,
                                instructional_group=group,
                                subject=subject,
                                requirement_type=requirement_type,
                                defaults={
                                    "lessons_per_week": weekly,
                                    "is_active": True,
                                },
                            )
                        )

                        if was_created:
                            created += 1
                            continue

                        changed = False

                        if (
                            requirement.lessons_per_week
                            != weekly
                        ):
                            requirement.lessons_per_week = weekly
                            changed = True

                        if not requirement.is_active:
                            requirement.is_active = True
                            changed = True

                        if changed:
                            requirement.save(
                                update_fields=[
                                    "lessons_per_week",
                                    "is_active",
                                    "updated_at",
                                ]
                            )
                            updated += 1

                legacy_codes = {
                    "COMP",
                    "HISTGOV",
                    "LIFE",
                }

                for group_code in GRADE10_GROUP_CODES:

                    group = groups[group_code]

                    legacy_requirements = (
                        LessonRequirement.objects
                        .select_for_update()
                        .filter(
                            term=term,
                            instructional_group=group,
                            is_active=True,
                            subject__code__in=legacy_codes,
                        )
                    )

                    for requirement in legacy_requirements:

                        requirement.is_active = False

                        requirement.save(
                            update_fields=[
                                "is_active",
                                "updated_at",
                            ]
                        )

                        deactivated_legacy += 1

            self.stdout.write("")
            self.stdout.write(
                "============================================================"
            )
            self.stdout.write(
                " MATERIALIZATION RESULT"
            )
            self.stdout.write(
                "============================================================"
            )

            self.stdout.write(
                f"TERM: {term}"
            )
            self.stdout.write(
                f"CREATED: {created}"
            )
            self.stdout.write(
                f"UPDATED: {updated}"
            )
            self.stdout.write(
                f"DEACTIVATED LEGACY: {deactivated_legacy}"
            )

            self.stdout.write("")
            self.stdout.write(
                "GENERATED CONTRACT ROWS:"
            )

            for group_code in (
                "10E",
                "10W",
                "3E",
                "3W",
                "4E",
                "4W",
            ):
                self.stdout.write(
                    f"  {group_code}: "
                    f"{expected_counts[group_code]}"
                )

            self.stdout.write("")
            self.stdout.write(
                "============================================================"
            )
            self.stdout.write(
                " ACTIVE REQUIREMENT READBACK"
            )
            self.stdout.write(
                "============================================================"
            )

            for group_code in (
                "10E",
                "10W",
                "3E",
                "3W",
                "4E",
                "4W",
            ):

                group = groups[group_code]

                requirements = list(
                    LessonRequirement.objects
                    .filter(
                        term=term,
                        instructional_group=group,
                        is_active=True,
                    )
                    .select_related("subject")
                    .order_by(
                        "requirement_type",
                        "subject__code",
                    )
                )

                counts = defaultdict(int)
                weekly = defaultdict(int)

                for requirement in requirements:

                    counts[
                        requirement.requirement_type
                    ] += 1

                    weekly[
                        requirement.requirement_type
                    ] += requirement.lessons_per_week

                self.stdout.write(
                    f"{group_code}: "
                    f"ROWS={len(requirements)} | "
                    f"STANDALONE="
                    f"{counts[LessonRequirementType.STANDALONE]}"
                    f"/{weekly[LessonRequirementType.STANDALONE]} | "
                    f"BLOCK="
                    f"{counts[LessonRequirementType.BLOCK]}"
                    f"/{weekly[LessonRequirementType.BLOCK]} | "
                    f"PRACTICAL="
                    f"{counts[LessonRequirementType.PRACTICAL]}"
                    f"/{weekly[LessonRequirementType.PRACTICAL]}"
                )

            self.stdout.write("")
            self.stdout.write(
                "============================================================"
            )
            self.stdout.write(
                " MATERIALIZATION: PASS"
            )
            self.stdout.write(
                "============================================================"
            )

        except Exception as exc:

            try:
                capture_exception(
                    exception=exc,
                    subsystem="academics",
                    operation=operation,
                    error_code=(
                        "SENIOR_SCHOOL_REQUIREMENT_"
                        "MATERIALIZATION_FAILED"
                    ),
                    message=(
                        "Senior School LessonRequirement "
                        "materialization failed."
                    ),
                    entity_type="LessonRequirement",
                    entity_id="",
                    solver_run_id="",
                    affected_teacher="",
                    affected_class="",
                    affected_subject="",
                    resolution="",
                    details={
                        "scope": [
                            "Grade 10",
                            "Form 3",
                            "Form 4",
                        ],
                    },
                )
            except Exception as capture_exc:

                self.stderr.write(
                    "ERROR CENTER CAPTURE FAILED: "
                    f"{type(capture_exc).__name__}: "
                    f"{capture_exc}"
                )

            self.stderr.write("")
            self.stderr.write(
                "============================================================"
            )
            self.stderr.write(
                " MATERIALIZATION: FAILED"
            )
            self.stderr.write(
                "============================================================"
            )
            self.stderr.write(
                f"EXCEPTION: "
                f"{type(exc).__module__}.{type(exc).__name__}"
            )
            self.stderr.write(
                f"MESSAGE: {exc}"
            )

            raise
