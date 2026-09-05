from __future__ import annotations

import time

from django.core.management.base import BaseCommand
from ortools.sat.python import cp_model

from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.objective import apply_solver_objectives
from apps.scheduling.models import SchedulingRun


class Command(BaseCommand):
    help = "Read-only profiler of the exact production CP-SAT model build."

    def handle(self, *args, **options):
        print()
        print("=" * 110)
        print("SMARTTIMETABLE PRO - EXACT PRODUCTION MODEL BUILD PROFILER")
        print("=" * 110)
        print("READ-ONLY: NO DATABASE CHANGES")
        print("READ-ONLY: NO SOLVER EXECUTION")
        print()

        run = (
            SchedulingRun.objects
            .filter(status="COMPLETED")
            .select_related("term", "timetable_version")
            .order_by("-completed_at", "-id")
            .first()
        )

        if run is None:
            raise RuntimeError("No completed SchedulingRun exists.")

        term = run.term

        print("REFERENCE COMPLETED RUN")
        print("-" * 110)
        print(f"RUN:           {run.id}")
        print(f"STATUS:        {run.status}")
        print(f"SOLVER STATUS: {run.solver_status}")
        print(f"VERSION:       {run.timetable_version}")
        print(f"OBJECTIVE:     {run.objective_value}")
        print()

        loader = DjangoSchedulingLoader()

        started = time.perf_counter()
        problem = loader.load_problem(term=term)
        load_time = time.perf_counter() - started

        print("PRODUCTION DOMAIN")
        print("-" * 110)
        print(f"REQUIREMENTS:         {len(problem.lesson_requirements)}")
        print(f"TEACHERS:             {len(problem.teachers)}")
        print(f"GROUPS:               {len(problem.instructional_groups)}")
        print(f"ROOMS:                {len(problem.rooms)}")
        print(f"PERIODS:              {len(problem.periods)}")
        print(f"SLOTS:                {len(problem.slots)}")
        print(f"TEACHER ASSIGNMENTS:  {len(problem.teacher_assignments)}")
        print(f"TEACHER AVAILABILITY: {len(problem.teacher_availability)}")
        print(f"FREE AFTERNOONS:      {len(problem.teacher_free_afternoons)}")
        print(f"ROOM AVAILABILITY:    {len(problem.room_availability)}")
        print(f"LOAD TIME:            {load_time:.6f}s")
        print()

        builder = SolverModelBuilder()
        model = cp_model.CpModel()

        def variable_count():
            return len(model.Proto().variables)

        def constraint_count():
            return len(model.Proto().constraints)

        def stage(label, callback):
            before_v = variable_count()
            before_c = constraint_count()

            started = time.perf_counter()
            result = callback()
            elapsed = time.perf_counter() - started

            after_v = variable_count()
            after_c = constraint_count()

            print(
                f"{label:<52}"
                f"{elapsed:>12.6f}s  "
                f"VARS +{after_v - before_v:<7}"
                f"CONSTRAINTS +{after_c - before_c:<7}"
                f"TOTAL {after_c}"
            )

            return result

        print("EXACT PRODUCTION BUILD STAGES")
        print("-" * 110)

        total_started = time.perf_counter()

        variables = stage(
            "CREATE ASSIGNMENT VARIABLES",
            lambda: builder._create_assignment_variables(
                model=model,
                problem=problem,
            ),
        )

        stage(
            "INSTITUTIONAL RESERVED PERIOD CONSTRAINTS",
            lambda: builder._add_institutional_reserved_period_constraints(
                model=model,
                problem=problem,
                variables=variables,
            ),
        )

        stage(
            "LESSON REQUIREMENT CONSTRAINTS",
            lambda: builder._add_lesson_requirement_constraints(
                model=model,
                problem=problem,
                variables=variables,
            ),
        )

        stage(
            "GRADE 10 OPTION BLOCK CONSTRAINTS",
            lambda: builder._add_grade10_option_block_constraints(
                model=model,
                problem=problem,
                variables=variables,
            ),
        )

        stage(
            "SIMULTANEOUS SUBJECT CONSTRAINTS",
            lambda: builder._add_simultaneous_subject_constraints(
                model=model,
                problem=problem,
                variables=variables,
            ),
        )

        stage(
            "TEACHER CLASH CONSTRAINTS",
            lambda: builder._add_teacher_clash_constraints(
                model=model,
                variables=variables,
            ),
        )

        stage(
            "GROUP CLASH CONSTRAINTS",
            lambda: builder._add_group_clash_constraints(
                model=model,
                problem=problem,
                variables=variables,
            ),
        )

        stage(
            "SINGLE LESSON PER DAY CONSTRAINTS",
            lambda: builder._add_single_lesson_per_day_constraints(
                model=model,
                problem=problem,
                variables=variables,
            ),
        )

        stage(
            "ROOM CLASH CONSTRAINTS",
            lambda: builder._add_room_clash_constraints(
                model=model,
                variables=variables,
            ),
        )

        stage(
            "TEACHER AVAILABILITY CONSTRAINTS",
            lambda: builder._add_teacher_availability_constraints(
                model=model,
                problem=problem,
                variables=variables,
            ),
        )

        stage(
            "TEACHER FREE AFTERNOON CONSTRAINTS",
            lambda: builder._add_teacher_free_afternoon_constraints(
                model=model,
                problem=problem,
                variables=variables,
            ),
        )

        stage(
            "ROOM AVAILABILITY CONSTRAINTS",
            lambda: builder._add_room_availability_constraints(
                model=model,
                problem=problem,
                variables=variables,
            ),
        )

        print()
        print("OBJECTIVE")
        print("-" * 110)

        before_objective = bool(model.Proto().objective)

        objective_started = time.perf_counter()

        apply_solver_objectives(
            model=model,
            problem=problem,
            variables=tuple(variables),
            objective=builder.objective,
        )

        objective_time = time.perf_counter() - objective_started
        after_objective = bool(model.Proto().objective)

        print(
            f"{'APPLY SOLVER OBJECTIVES':<52}"
            f"{objective_time:>12.6f}s  "
            f"OBJECTIVE {before_objective} -> {after_objective}"
        )

        total_time = time.perf_counter() - total_started

        print()
        print("=" * 110)
        print("FINAL EXACT PRODUCTION MODEL")
        print("=" * 110)
        print(f"VARIABLES:        {variable_count()}")
        print(f"CONSTRAINTS:      {constraint_count()}")
        print(f"HAS OBJECTIVE:    {bool(model.Proto().objective)}")
        print(f"TOTAL BUILD TIME: {total_time:.6f}s")
        print()

        expected_variables = (
            len(problem.lesson_requirements)
            * len(problem.slots)
            * len(problem.rooms)
        )

        print("DIMENSION CHECK")
        print("-" * 110)
        print(f"EXPECTED VARIABLES: {expected_variables}")
        print(f"ACTUAL VARIABLES:   {variable_count()}")

        if expected_variables != variable_count():
            raise RuntimeError(
                "Production model variable dimension mismatch."
            )

        print()
        print("RESULT: PASS")
        print("Exact production constraint sequence constructed.")
        print("No solver execution occurred.")
        print("No database changes occurred.")
        print()
        print("=" * 110)
        print("READ-ONLY COMPLETE")
        print("=" * 110)
        print()


