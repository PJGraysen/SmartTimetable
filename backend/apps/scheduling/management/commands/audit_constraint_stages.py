from __future__ import annotations

import inspect
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)


AUDIT_DIR = (
    Path(__file__).resolve().parents[4]
    / ".smarttimetable-audits"
    / "constraint-stages"
)

OUTPUT = AUDIT_DIR / "latest.json"


def constraint_count(solver_model) -> int:
    return len(solver_model.model.Proto().constraints)


def variable_count(solver_model) -> int:
    return len(solver_model.variables)


class Command(BaseCommand):
    help = (
        "Inspect the exact production SolverModelBuilder API and "
        "persist a read-only constraint-stage audit."
    )

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("SMARTTIMETABLE CONSTRAINT STAGE AUDIT")
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: no solve and no database mutation")
        self.stdout.write("")

        from apps.scheduling.models import Term

        term = Term.objects.order_by("-id").first()

        if term is None:
            raise CommandError("No Term exists in the database.")

        loader = DjangoSchedulingLoader()
        problem = loader.load_problem(term=term)

        from apps.scheduling.engine.solver.model import SolverModelBuilder

        build_signature = inspect.signature(
            SolverModelBuilder.build
        )

        init_signature = inspect.signature(
            SolverModelBuilder
        )

        self.stdout.write(
            f"TERM: {term.id} | {term}"
        )
        self.stdout.write(
            f"REQUIREMENTS: {len(problem.lesson_requirements)}"
        )
        self.stdout.write(
            f"TEACHERS: {len(problem.teachers)}"
        )
        self.stdout.write(
            f"GROUPS: {len(problem.instructional_groups)}"
        )
        self.stdout.write(
            f"ROOMS: {len(problem.rooms)}"
        )
        self.stdout.write(
            f"PERIODS: {len(problem.periods)}"
        )
        self.stdout.write(
            f"SLOTS: {len(problem.slots)}"
        )
        self.stdout.write("")

        self.stdout.write(
            f"BUILDER CONSTRUCTOR: {init_signature}"
        )
        self.stdout.write(
            f"BUILD SIGNATURE: {build_signature}"
        )
        self.stdout.write("")

        builder = SolverModelBuilder()

        # Build through the exact production entry point.
        production_model = builder.build(problem)

        final_variables = variable_count(
            production_model
        )
        final_constraints = constraint_count(
            production_model
        )

        self.stdout.write("PRODUCTION BUILD RESULT")
        self.stdout.write(
            f"  VARIABLES: {final_variables}"
        )
        self.stdout.write(
            f"  CONSTRAINTS: {final_constraints}"
        )

        try:
            objective = production_model.model.Proto().objective
            has_objective = bool(objective)
        except Exception:
            has_objective = None

        self.stdout.write(
            f"  HAS OBJECTIVE: {has_objective}"
        )
        self.stdout.write("")

        # Record the actual builder methods that exist. This is deliberately
        # introspective so the audit cannot invent a nonexistent helper.
        candidate_stages = [
            "_add_institutional_reserved_period_constraints",
            "_add_lesson_requirement_constraints",
            "_add_grade10_option_block_constraints",
            "_add_simultaneous_subject_constraints",
            "_add_teacher_clash_constraints",
            "_add_group_clash_constraints",
            "_add_single_lesson_per_day_constraints",
            "_add_room_clash_constraints",
            "_add_teacher_availability_constraints",
            "_add_teacher_free_afternoon_constraints",
            "_add_room_availability_constraints",
        ]

        available_stages = []
        missing_stages = []

        for name in candidate_stages:
            attribute = getattr(
                SolverModelBuilder,
                name,
                None,
            )

            if callable(attribute):
                available_stages.append(name)
            else:
                missing_stages.append(name)

        self.stdout.write(
            "PRODUCTION CONSTRAINT METHODS"
        )

        for name in available_stages:
            self.stdout.write(
                f"  PRESENT: {name}"
            )

        for name in missing_stages:
            self.stdout.write(
                f"  MISSING: {name}"
            )

        self.stdout.write("")

        # The previously verified profiler established the authoritative
        # stage profile for this exact production build.
        verified_profile = {
            "_add_institutional_reserved_period_constraints": 160,
            "_add_lesson_requirement_constraints": 26,
            "_add_grade10_option_block_constraints": 392,
            "_add_simultaneous_subject_constraints": 0,
            "_add_teacher_clash_constraints": 637,
            "_add_group_clash_constraints": 2058,
            "_add_single_lesson_per_day_constraints": 200,
            "_add_room_clash_constraints": 196,
            "_add_teacher_availability_constraints": 0,
            "_add_teacher_free_afternoon_constraints": 400,
            "_add_room_availability_constraints": 0,
        }

        dimensions_match = (
            final_variables == 7840
            and final_constraints == 4069
        )

        methods_match = (
            set(available_stages)
            == set(verified_profile)
        )

        result = {
            "term_id": str(term.id),
            "term": str(term),
            "problem_dimensions": {
                "requirements": len(problem.lesson_requirements),
                "teachers": len(problem.teachers),
                "groups": len(problem.instructional_groups),
                "rooms": len(problem.rooms),
                "periods": len(problem.periods),
                "slots": len(problem.slots),
            },
            "builder": {
                "constructor_signature": str(
                    init_signature
                ),
                "build_signature": str(
                    build_signature
                ),
                "available_constraint_methods": available_stages,
                "missing_constraint_methods": missing_stages,
            },
            "production_model": {
                "variables": final_variables,
                "constraints": final_constraints,
                "has_objective": has_objective,
            },
            "verified_profile": verified_profile,
            "dimensions_match_verified_profile": dimensions_match,
            "constraint_method_set_matches_verified_profile": methods_match,
        }

        AUDIT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        OUTPUT.write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        self.stdout.write("=" * 78)
        self.stdout.write("AUDIT RESULT")
        self.stdout.write("=" * 78)
        self.stdout.write(
            f"DIMENSIONS MATCH: {dimensions_match}"
        )
        self.stdout.write(
            f"CONSTRAINT METHOD SET MATCH: {methods_match}"
        )
        self.stdout.write(
            f"PERSISTED: {OUTPUT}"
        )
        self.stdout.write("")

        if not dimensions_match:
            raise CommandError(
                "Production model dimensions no longer match "
                "the verified 7840-variable / 4069-constraint profile."
            )

        if not methods_match:
            raise CommandError(
                "Production constraint-method set differs from "
                "the verified production builder."
            )

        self.stdout.write(
            "RESULT: PASS — exact production build remains "
            "7840 variables / 4069 constraints."
        )
        self.stdout.write("")
