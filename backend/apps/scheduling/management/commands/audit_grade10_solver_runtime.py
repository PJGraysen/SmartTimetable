from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.scheduling.engine.application.grade10_parallel_blocks import (
    GRADE10_PARALLEL_BLOCKS,
    get_grade10_parallel_block_for_subject,
    validate_grade10_parallel_blocks,
)
from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)
from apps.scheduling.engine.solver.model import SolverModel
from apps.scheduling.engine.solver.model_builder import SolverModelBuilder
from apps.scheduling.engine.domain.entities import DayOfWeek
from apps.academics.models import Term


class Command(BaseCommand):
    help = (
        "Read-only Grade 10 solver runtime audit. "
        "Builds and solves the actual CP-SAT model and verifies "
        "Grade 10 weekly quotas and synchronized option blocks."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(
            "============================================================================"
        )
        self.stdout.write(
            "SMARTTIMETABLE PRO - GRADE 10 SOLVER RUNTIME AUDIT"
        )
        self.stdout.write(
            "============================================================================"
        )
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        validate_grade10_parallel_blocks()

        self.stdout.write("=== AUTHORITATIVE PARALLEL BLOCKS ===")

        for block in GRADE10_PARALLEL_BLOCKS:
            self.stdout.write(
                f"{block.code}: "
                f"{' / '.join(block.subject_codes)} "
                f"= {block.weekly_shared_slots} shared slots/week"
            )

        self.stdout.write("")

        term = (
            Term.objects
            .filter(is_active=True)
            .order_by("-start_date", "-id")
            .first()
        )

        if term is None:
            raise CommandError(
                "No active Term exists."
            )

        self.stdout.write("=== RUNTIME TERM ===")
        self.stdout.write(f"TERM ID: {term.id}")
        self.stdout.write(f"TERM: {term}")
        self.stdout.write("")

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

        self.stdout.write("=== RUNTIME PROBLEM COUNTS ===")
        self.stdout.write(f"PERIODS: {len(problem.periods)}")
        self.stdout.write(f"SLOTS: {len(problem.slots)}")
        self.stdout.write(f"TEACHERS: {len(problem.teachers)}")
        self.stdout.write(
            f"INSTRUCTIONAL GROUPS: "
            f"{len(problem.instructional_groups)}"
        )
        self.stdout.write(f"ROOMS: {len(problem.rooms)}")
        self.stdout.write(
            f"LESSON REQUIREMENTS: "
            f"{len(problem.lesson_requirements)}"
        )
        self.stdout.write(
            f"TEACHER ASSIGNMENTS: "
            f"{len(problem.teacher_assignments)}"
        )
        self.stdout.write("")

        grade10_groups = {
            group.id: group
            for group in problem.instructional_groups
            if group.is_active
            and (
                str(group.code).upper().startswith("10")
                or "GRADE 10" in str(group.name).upper()
            )
        }

        if not grade10_groups:
            raise CommandError(
                "No Grade 10 instructional groups were found "
                "in the runtime SchedulingProblem."
            )

        self.stdout.write("=== GRADE 10 RUNTIME GROUPS ===")

        for group in grade10_groups.values():
            self.stdout.write(
                f"GROUP: {group.id} | "
                f"CODE={group.code} | "
                f"NAME={group.name}"
            )

        self.stdout.write("")

        grade10_requirements = [
            requirement
            for requirement in problem.lesson_requirements
            if requirement.is_active
            and requirement.instructional_group_id
            in grade10_groups
        ]

        if not grade10_requirements:
            raise CommandError(
                "No active Grade 10 lesson requirements were found."
            )

        self.stdout.write("=== BUILDING ACTUAL SOLVER MODEL ===")

        builder = SolverModelBuilder()

        solver_model = builder.build(problem)

        self.stdout.write(
            "PASS - Actual SolverModel built successfully."
        )

        self.stdout.write(
            f"ASSIGNMENT VARIABLES: "
            f"{len(solver_model.variables)}"
        )
        self.stdout.write("")

        self.stdout.write("=== SOLVING ACTUAL CP-SAT MODEL ===")

        from ortools.sat.python import cp_model

        solver = cp_model.CpSolver()

        status = solver.solve(
            solver_model.model
        )

        status_name = solver.status_name(status)

        self.stdout.write(
            f"SOLVER STATUS: {status_name}"
        )

        if status not in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        ):
            raise CommandError(
                "Actual Grade 10 solver model did not produce "
                f"a usable solution. STATUS={status_name}"
            )

        self.stdout.write(
            "PASS - Actual CP-SAT model produced a usable solution."
        )
        self.stdout.write("")

        selected = []

        for variable in solver_model.variables:
            if solver.value(variable.variable) != 1:
                continue

            if variable.instructional_group_id not in grade10_groups:
                continue

            selected.append(variable)

        self.stdout.write("=== SELECTED GRADE 10 ASSIGNMENTS ===")

        if not selected:
            raise CommandError(
                "Solver returned no selected Grade 10 assignments."
            )

        requirements_by_id = {
            requirement.id: requirement
            for requirement in grade10_requirements
        }

        selected_by_requirement: dict[
            UUID,
            list[Any],
        ] = defaultdict(list)

        for variable in selected:
            selected_by_requirement[
                variable.lesson_requirement_id
            ].append(variable)

        quota_failures = []

        self.stdout.write("")

        for group_id, group in grade10_groups.items():

            self.stdout.write(
                f"GROUP: {group.code}"
            )

            group_requirements = [
                requirement
                for requirement in grade10_requirements
                if requirement.instructional_group_id == group_id
            ]

            for requirement in sorted(
                group_requirements,
                key=lambda item: item.subject_code,
            ):

                actual = len(
                    selected_by_requirement.get(
                        requirement.id,
                        [],
                    )
                )

                expected = requirement.periods_per_week

                block = get_grade10_parallel_block_for_subject(
                    requirement.subject_code
                )

                if actual == expected:
                    result = "PASS"
                else:
                    result = "FAIL"
                    quota_failures.append(
                        (
                            group.code,
                            requirement.subject_code,
                            expected,
                            actual,
                        )
                    )

                if block is None:
                    category = "CORE"
                else:
                    category = block.code

                self.stdout.write(
                    f"  {result} - "
                    f"{requirement.subject_code}: "
                    f"runtime={actual}/week "
                    f"expected={expected}/week "
                    f"| {category}"
                )

            self.stdout.write("")

        if quota_failures:
            self.stdout.write(
                "FAIL - One or more Grade 10 weekly quotas "
                "were not satisfied."
            )
        else:
            self.stdout.write(
                "PASS - All Grade 10 weekly quotas are satisfied "
                "by the actual solver solution."
            )

        self.stdout.write("")

        self.stdout.write(
            "=== PARALLEL BLOCK SYNCHRONIZATION AUDIT ==="
        )

        synchronization_failures = []

        for group_id, group in grade10_groups.items():

            self.stdout.write("")
            self.stdout.write(
                f"GROUP: {group.code}"
            )

            for block in GRADE10_PARALLEL_BLOCKS:

                subject_requirements = {
                    subject_code: next(
                        (
                            requirement
                            for requirement in grade10_requirements
                            if (
                                requirement.instructional_group_id
                                == group_id
                                and requirement.subject_code
                                == subject_code
                            )
                        ),
                        None,
                    )
                    for subject_code in block.subject_codes
                }

                slot_sets = {}

                for subject_code, requirement in (
                    subject_requirements.items()
                ):

                    if requirement is None:
                        slot_sets[subject_code] = set()
                        continue

                    slot_sets[subject_code] = {
                        (
                            variable.day,
                            variable.period_id,
                        )
                        for variable in selected_by_requirement.get(
                            requirement.id,
                            [],
                        )
                    }

                expected_count = block.weekly_shared_slots

                all_match = (
                    len(
                        {
                            frozenset(slots)
                            for slots in slot_sets.values()
                        }
                    )
                    == 1
                )

                correct_count = all(
                    len(slots) == expected_count
                    for slots in slot_sets.values()
                )

                if all_match and correct_count:
                    self.stdout.write(
                        f"PASS - {block.code}: "
                        f"{' / '.join(block.subject_codes)} "
                        f"share exactly "
                        f"{expected_count} slots"
                    )
                else:
                    synchronization_failures.append(
                        (
                            group.code,
                            block.code,
                            slot_sets,
                        )
                    )

                    self.stdout.write(
                        f"FAIL - {block.code}: "
                        f"{' / '.join(block.subject_codes)}"
                    )

                    for subject_code, slots in slot_sets.items():
                        self.stdout.write(
                            f"    {subject_code}: "
                            f"{len(slots)} slots -> "
                            f"{sorted(slots)}"
                        )

        self.stdout.write("")

        self.stdout.write(
            "=== FINAL GRADE 10 SOLVER AUDIT ==="
        )

        if quota_failures:
            self.stdout.write(
                "FAIL - Weekly quota validation failed."
            )

        else:
            self.stdout.write(
                "PASS - Weekly quota validation."
            )

        if synchronization_failures:
            self.stdout.write(
                "FAIL - Parallel block synchronization failed."
            )
        else:
            self.stdout.write(
                "PASS - Parallel block synchronization."
            )

        self.stdout.write("")

        if quota_failures or synchronization_failures:
            self.stdout.write(
                "============================================================================"
            )
            self.stdout.write(
                "GRADE 10 SOLVER RUNTIME AUDIT: FAIL"
            )
            self.stdout.write(
                "The actual solver model does not yet satisfy "
                "the complete Grade 10 academic contract."
            )
            self.stdout.write(
                "NO DATABASE CHANGES WERE MADE."
            )
            self.stdout.write(
                "============================================================================"
            )

            raise CommandError(
                "Grade 10 solver runtime audit failed."
            )

        self.stdout.write(
            "============================================================================"
        )
        self.stdout.write(
            "GRADE 10 SOLVER RUNTIME AUDIT: PASS"
        )
        self.stdout.write(
            "The actual CP-SAT solution satisfies the "
            "Grade 10 weekly quota and parallel-block checks."
        )
        self.stdout.write(
            "NO DATABASE CHANGES WERE MADE."
        )
        self.stdout.write(
            "============================================================================"
        )
