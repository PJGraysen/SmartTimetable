from __future__ import annotations

import inspect
import time
from itertools import combinations

from django.core.management.base import BaseCommand
from ortools.sat.python import cp_model

from apps.core.models import Term
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder


class Command(BaseCommand):
    help = "Read-only production constraint isolation diagnostic."

    CONSTRAINT_FAMILIES = (
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
    )

    CANDIDATES = (
        "_add_institutional_reserved_period_constraints",
        "_add_lesson_requirement_constraints",
        "_add_group_clash_constraints",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--time-limit",
            type=float,
            default=30.0,
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=1,
        )

    def handle(self, *args, **options):
        time_limit = options["time_limit"]
        workers = options["workers"]

        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write(
            "SMARTTIMETABLE PRO - PRODUCTION CONSTRAINT ISOLATION"
        )
        self.stdout.write("=" * 100)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        term = (
            Term.objects
            .order_by("-id")
            .first()
        )

        if term is None:
            raise RuntimeError("No Term exists in the database.")

        loader = DjangoSchedulingLoader()
        problem = loader.load_problem(term=term)

        self.stdout.write(f"TERM: {term}")
        self.stdout.write(f"REQUIREMENTS: {len(problem.lesson_requirements)}")
        self.stdout.write(f"TEACHERS:     {len(problem.teachers)}")
        self.stdout.write(f"GROUPS:       {len(problem.instructional_groups)}")
        self.stdout.write(f"ROOMS:        {len(problem.rooms)}")
        self.stdout.write(f"PERIODS:      {len(problem.periods)}")
        self.stdout.write(f"SLOTS:        {len(problem.slots)}")
        self.stdout.write("")

        builder = SolverModelBuilder()

        self.stdout.write("VERIFIED PRODUCTION CONSTRAINT SIGNATURES")
        self.stdout.write("-" * 100)

        for name in self.CONSTRAINT_FAMILIES:
            method = getattr(builder, name)
            self.stdout.write(f"{name}")
            self.stdout.write(f"  {inspect.signature(method)}")

        self.stdout.write("")

        def apply_constraint(name, model, variables):
            method = getattr(builder, name)
            signature = inspect.signature(method)

            available = {
                "model": model,
                "problem": problem,
                "variables": variables,
            }

            kwargs = {
                key: value
                for key, value in available.items()
                if key in signature.parameters
            }

            method(**kwargs)

        def build_model(excluded):
            model = cp_model.CpModel()

            variables = builder._create_assignment_variables(
                model=model,
                problem=problem,
            )

            for name in self.CONSTRAINT_FAMILIES:
                if name in excluded:
                    continue

                apply_constraint(
                    name,
                    model,
                    variables,
                )

            return model

        def solve(excluded):
            started = time.perf_counter()

            model = build_model(excluded)

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = time_limit
            solver.parameters.num_workers = workers

            status = solver.Solve(model)

            elapsed = time.perf_counter() - started

            return {
                "status": solver.StatusName(status),
                "elapsed": elapsed,
                "conflicts": solver.NumConflicts(),
                "branches": solver.NumBranches(),
            }

        self.stdout.write("BASELINE")
        self.stdout.write("-" * 100)

        baseline = solve(set())

        self.stdout.write(
            "ALL CONSTRAINTS"
            f"  {baseline['status']:<10}"
            f" time={baseline['elapsed']:7.3f}s"
            f" conflicts={baseline['conflicts']:7d}"
            f" branches={baseline['branches']:8d}"
        )

        self.stdout.write("")
        self.stdout.write("SINGLE CANDIDATE REMOVAL")
        self.stdout.write("-" * 100)

        single_results = {}

        for name in self.CANDIDATES:
            result = solve({name})
            single_results[name] = result

            self.stdout.write(
                f"REMOVE {name:<55}"
                f" {result['status']:<10}"
                f" time={result['elapsed']:7.3f}s"
                f" conflicts={result['conflicts']:7d}"
                f" branches={result['branches']:8d}"
            )

        self.stdout.write("")
        self.stdout.write("PAIRWISE CANDIDATE REMOVAL")
        self.stdout.write("-" * 100)

        pair_results = {}

        for first, second in combinations(self.CANDIDATES, 2):
            result = solve({first, second})
            pair_results[(first, second)] = result

            self.stdout.write(
                f"REMOVE BOTH"
            )
            self.stdout.write(f"  {first}")
            self.stdout.write(f"  {second}")
            self.stdout.write(
                f"  => {result['status']}"
                f" time={result['elapsed']:7.3f}s"
                f" conflicts={result['conflicts']:7d}"
                f" branches={result['branches']:8d}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write("RESULT")
        self.stdout.write("=" * 100)

        feasible_single = [
            name
            for name, result in single_results.items()
            if result["status"] in ("FEASIBLE", "OPTIMAL")
        ]

        feasible_pairs = [
            pair
            for pair, result in pair_results.items()
            if result["status"] in ("FEASIBLE", "OPTIMAL")
        ]

        if feasible_single:
            self.stdout.write(
                "SINGLE REMOVALS RESTORING FEASIBILITY:"
            )
            for name in feasible_single:
                self.stdout.write(f"  -> {name}")
        else:
            self.stdout.write(
                "SINGLE REMOVALS RESTORING FEASIBILITY: NONE"
            )

        self.stdout.write("")

        if feasible_pairs:
            self.stdout.write(
                "PAIR REMOVALS RESTORING FEASIBILITY:"
            )
            for first, second in feasible_pairs:
                self.stdout.write(f"  -> {first}")
                self.stdout.write(f"     {second}")
        else:
            self.stdout.write(
                "PAIR REMOVALS RESTORING FEASIBILITY: NONE"
            )

        self.stdout.write("")
        self.stdout.write(
            "UNKNOWN means the diagnostic time limit expired;"
        )
        self.stdout.write(
            "it does NOT mean INFEASIBLE."
        )
        self.stdout.write("")
        self.stdout.write(
            "This diagnostic does not modify production code,"
        )
        self.stdout.write(
            "database records, timetable entries, or scheduling runs."
        )
        self.stdout.write("=" * 100)
