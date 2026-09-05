from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from apps.scheduling.engine.application.grade10_parallel_blocks import (
    GRADE10_PARALLEL_BLOCKS,
    GRADE10_PARALLEL_SUBJECT_TO_BLOCK,
    describe_grade10_parallel_blocks,
    validate_grade10_parallel_blocks,
)
from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)
from apps.scheduling.models import Term


class Command(BaseCommand):
    help = (
        "Trace the actual Django-loaded SchedulingProblem for Grade 10 "
        "requirements. READ-ONLY."
    )

    def handle(self, *args, **options):
        self.stdout.write("=" * 76)
        self.stdout.write(
            "SMARTTIMETABLE PRO - GRADE 10 RUNTIME REQUIREMENT TRACE"
        )
        self.stdout.write("=" * 76)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        # ==============================================================
        # AUTHORITATIVE CONTRACT
        # ==============================================================

        validate_grade10_parallel_blocks()

        self.stdout.write("=== AUTHORITATIVE PARALLEL BLOCKS ===")

        for description in describe_grade10_parallel_blocks():
            self.stdout.write(description)

        self.stdout.write("")

        # ==============================================================
        # RESOLVE RUNTIME TERM
        # ==============================================================

        terms = list(
            Term.objects.all().order_by("-id")
        )

        if not terms:
            raise CommandError(
                "No Term records exist. "
                "Cannot construct the runtime SchedulingProblem."
            )

        active_terms = [
            term
            for term in terms
            if getattr(term, "is_active", False)
        ]

        if len(active_terms) == 1:
            term = active_terms[0]

        elif len(terms) == 1:
            term = terms[0]

        else:
            raise CommandError(
                "Unable to safely select a single runtime Term. "
                f"Found {len(terms)} terms and "
                f"{len(active_terms)} active terms. "
                "The trace will not guess between terms."
            )

        self.stdout.write("=== RUNTIME TERM ===")
        self.stdout.write(f"TERM ID: {term.pk}")
        self.stdout.write(f"TERM: {term}")
        self.stdout.write("")

        # ==============================================================
        # ACTUAL DJANGO LOADER API
        # ==============================================================

        loader = DjangoSchedulingLoader()

        self.stdout.write("=== ACTUAL LOADER ===")
        self.stdout.write(
            "CALL: DjangoSchedulingLoader.load_problem(term=term)"
        )

        problem = loader.load_problem(term=term)

        self.stdout.write(
            "PASS - Actual SchedulingProblem loaded successfully."
        )
        self.stdout.write("")

        # ==============================================================
        # RUNTIME PROBLEM COUNTS
        # ==============================================================

        self.stdout.write("=== RUNTIME PROBLEM COUNTS ===")
        self.stdout.write(
            f"PERIODS: {len(problem.periods)}"
        )
        self.stdout.write(
            f"SLOTS: {len(problem.slots)}"
        )
        self.stdout.write(
            f"TEACHERS: {len(problem.teachers)}"
        )
        self.stdout.write(
            f"INSTRUCTIONAL GROUPS: "
            f"{len(problem.instructional_groups)}"
        )
        self.stdout.write(
            f"ROOMS: {len(problem.rooms)}"
        )
        self.stdout.write(
            f"LESSON REQUIREMENTS: "
            f"{len(problem.lesson_requirements)}"
        )
        self.stdout.write(
            f"TEACHER ASSIGNMENTS: "
            f"{len(problem.teacher_assignments)}"
        )
        self.stdout.write("")

        # ==============================================================
        # FIND GRADE 10 GROUPS
        # ==============================================================

        grade10_groups = [
            group
            for group in problem.instructional_groups
            if getattr(group, "is_active", True)
            and (
                str(getattr(group, "code", "")) in {"10E", "10W"}
            )
        ]

        self.stdout.write("=== GRADE 10 RUNTIME GROUPS ===")

        if not grade10_groups:
            raise CommandError(
                "No Grade 10 instructional groups were found."
            )

        for group in grade10_groups:
            self.stdout.write(
                f"GROUP: {group.id} | "
                f"CODE={group.code} | "
                f"NAME={group.name}"
            )

        self.stdout.write("")

        grade10_group_ids = {
            group.id
            for group in grade10_groups
        }

        # ==============================================================
        # GRADE 10 RUNTIME REQUIREMENTS
        # ==============================================================

        grade10_requirements = [
            requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
            and requirement.instructional_group_id
            in grade10_group_ids
        ]

        if not grade10_requirements:
            raise CommandError(
                "The actual runtime SchedulingProblem contains no "
                "active Grade 10 LessonRequirements."
            )

        requirements_by_group = defaultdict(list)

        for requirement in grade10_requirements:
            requirements_by_group[
                requirement.instructional_group_id
            ].append(requirement)

        groups_by_id = {
            group.id: group
            for group in grade10_groups
        }

        self.stdout.write(
            "=== GRADE 10 RUNTIME LESSON REQUIREMENTS ==="
        )

        for group_id in sorted(
            requirements_by_group,
            key=lambda value: str(
                groups_by_id[value].code
            ),
        ):
            group = groups_by_id[group_id]

            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group.code} | {group.name}"
            )

            group_requirements = sorted(
                requirements_by_group[group_id],
                key=lambda requirement: (
                    str(requirement.subject_code),
                    str(requirement.id),
                ),
            )

            self.stdout.write(
                f"ACTIVE REQUIREMENTS: "
                f"{len(group_requirements)}"
            )

            for requirement in group_requirements:

                block_code = GRADE10_PARALLEL_SUBJECT_TO_BLOCK.get(
                    requirement.subject_code
                )

                if block_code is None:
                    block_label = "CORE"
                else:
                    block_label = block_code

                self.stdout.write(
                    f"  {requirement.subject_code}: "
                    f"{requirement.periods_per_week}/week "
                    f"| {block_label} "
                    f"| requirement={requirement.id}"
                )

        self.stdout.write("")

        # ==============================================================
        # AUTHORITATIVE WEEKLY QUOTAS
        # ==============================================================

        expected = {
            "ENG": 5,
            "KIS": 5,
            "EMCM": 5,
            "CRE": 4,
            "PE": 3,
            "CSL": 3,
            "ICT": 2,
            "PRP": 1,
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

        self.stdout.write(
            "=== RUNTIME VS AUTHORITATIVE WEEKLY QUOTAS ==="
        )

        all_passed = True

        for group_id in sorted(
            requirements_by_group,
            key=lambda value: str(
                groups_by_id[value].code
            ),
        ):
            group = groups_by_id[group_id]

            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group.code}"
            )

            runtime_by_subject = {
                requirement.subject_code: requirement.periods_per_week
                for requirement in requirements_by_group[group_id]
            }

            for subject_code, expected_count in expected.items():

                actual_count = runtime_by_subject.get(
                    subject_code
                )

                if actual_count == expected_count:
                    self.stdout.write(
                        f"PASS - {subject_code}: "
                        f"runtime={actual_count}/week "
                        f"expected={expected_count}/week"
                    )
                else:
                    all_passed = False

                    self.stdout.write(
                        f"FAIL - {subject_code}: "
                        f"runtime={actual_count}/week "
                        f"expected={expected_count}/week"
                    )

        self.stdout.write("")

        # ==============================================================
        # TEACHER ASSIGNMENT TRACE
        # ==============================================================

        self.stdout.write(
            "=== GRADE 10 TEACHER ASSIGNMENT TRACE ==="
        )

        teacher_by_id = {
            teacher.id: teacher
            for teacher in problem.teachers
        }

        requirement_by_id = {
            requirement.id: requirement
            for requirement in grade10_requirements
        }

        assignments_by_requirement = defaultdict(list)

        for assignment in problem.teacher_assignments:

            if not assignment.is_active:
                continue

            if assignment.lesson_requirement_id not in requirement_by_id:
                continue

            assignments_by_requirement[
                assignment.lesson_requirement_id
            ].append(assignment)

        for requirement in sorted(
            grade10_requirements,
            key=lambda item: (
                str(item.instructional_group_id),
                str(item.subject_code),
            ),
        ):
            assignments = assignments_by_requirement.get(
                requirement.id,
                [],
            )

            teacher_codes = []

            for assignment in assignments:

                teacher = teacher_by_id.get(
                    assignment.teacher_id
                )

                if teacher is None:
                    teacher_codes.append(
                        str(assignment.teacher_id)
                    )
                else:
                    teacher_codes.append(
                        str(teacher.code)
                    )

            teacher_text = (
                ", ".join(sorted(set(teacher_codes)))
                if teacher_codes
                else "NONE"
            )

            self.stdout.write(
                f"{requirement.subject_code}: "
                f"{requirement.periods_per_week}/week "
                f"| teachers={teacher_text}"
            )

        self.stdout.write("")

        # ==============================================================
        # PARALLEL BLOCK RUNTIME PRESENCE
        # ==============================================================

        self.stdout.write(
            "=== RUNTIME PARALLEL BLOCK PRESENCE ==="
        )

        subjects_by_block = defaultdict(list)

        for subject_code, block_code in (
            GRADE10_PARALLEL_SUBJECT_TO_BLOCK.items()
        ):
            subjects_by_block[block_code].append(
                subject_code
            )

        for block in GRADE10_PARALLEL_BLOCKS:

            block_code = block.code

            block_subjects = sorted(
                subjects_by_block.get(
                    block_code,
                    [],
                )
            )

            self.stdout.write("")
            self.stdout.write(
                f"{block_code}: "
                f"{' / '.join(block_subjects)}"
            )

            for group_id in sorted(
                requirements_by_group,
                key=lambda value: str(
                    groups_by_id[value].code
                ),
            ):
                group = groups_by_id[group_id]

                runtime_subjects = {
                    requirement.subject_code
                    for requirement in requirements_by_group[
                        group_id
                    ]
                }

                missing = [
                    subject
                    for subject in block_subjects
                    if subject not in runtime_subjects
                ]

                if missing:
                    all_passed = False

                    self.stdout.write(
                        f"FAIL - {group.code}: "
                        f"missing {', '.join(missing)}"
                    )
                else:
                    self.stdout.write(
                        f"PASS - {group.code}: "
                        f"all subjects present"
                    )

        self.stdout.write("")

        # ==============================================================
        # REQUIREMENT ROW COUNT
        # ==============================================================

        self.stdout.write(
            "=== REQUIREMENT ROW COUNT ==="
        )

        for group_id in sorted(
            requirements_by_group,
            key=lambda value: str(
                groups_by_id[value].code
            ),
        ):
            group = groups_by_id[group_id]
            count = len(
                requirements_by_group[group_id]
            )

            if count == 20:
                self.stdout.write(
                    f"PASS - {group.code}: "
                    f"{count} active Grade 10 requirements"
                )
            else:
                all_passed = False
                self.stdout.write(
                    f"FAIL - {group.code}: "
                    f"{count} active Grade 10 requirements "
                    f"(expected 20)"
                )

        self.stdout.write("")

        # ==============================================================
        # FINAL RESULT
        # ==============================================================

        self.stdout.write("=" * 76)

        if all_passed:
            self.stdout.write(
                "GRADE 10 RUNTIME REQUIREMENT TRACE: PASS"
            )
            self.stdout.write(
                "The actual DjangoSchedulingLoader runtime problem "
                "contains the authoritative Grade 10 weekly quotas "
                "and parallel subject structure."
            )
        else:
            self.stdout.write(
                "GRADE 10 RUNTIME REQUIREMENT TRACE: FAIL"
            )
            self.stdout.write(
                "The actual runtime SchedulingProblem does not fully "
                "match the authoritative Grade 10 academic contract."
            )

        self.stdout.write(
            "NO DATABASE CHANGES WERE MADE."
        )

        self.stdout.write("=" * 76)
