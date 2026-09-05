from __future__ import annotations

import copy
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand

from ortools.sat.python import cp_model

from apps.scheduling.models import SchedulingRun
from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver


KNOWN_GOOD_RUN_ID = "8eccf5f8-c91a-439a-9970-297abfbdc403"
TIME_LIMIT_SECONDS = 120.0


class Command(BaseCommand):
    help = "Run a read-only controlled CP-SAT solver reproduction."

    def handle(self, *args, **options):
        backend_root = Path(__file__).resolve().parents[4]

        audit_dir = (
            backend_root
            / "backend"
            / ".smarttimetable-audits"
            / "controlled-solver-reproduction"
        )
        audit_dir.mkdir(parents=True, exist_ok=True)

        output_path = audit_dir / "latest.json"

        self.stdout.write("=" * 78)
        self.stdout.write(
            "SMARTTIMETABLE CONTROLLED CP-SAT SOLVER REPRODUCTION"
        )
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: no database mutation")
        self.stdout.write("READ-ONLY: no timetable persistence")
        self.stdout.write("")

        known_good_run = (
            SchedulingRun.objects
            .select_related("term")
            .get(id=KNOWN_GOOD_RUN_ID)
        )

        term = known_good_run.term

        self.stdout.write(f"TERM: {term.id} | {term}")
        self.stdout.write(f"KNOWN-GOOD RUN: {known_good_run.id}")
        self.stdout.write("")

        loader = DjangoSchedulingLoader()
        problem = loader.load_problem(term=term)

        self.stdout.write("PROBLEM")
        self.stdout.write(
            f"  REQUIREMENTS: {len(problem.lesson_requirements)}"
        )
        self.stdout.write(f"  TEACHERS: {len(problem.teachers)}")
        self.stdout.write(
            f"  GROUPS: {len(problem.instructional_groups)}"
        )
        self.stdout.write(f"  ROOMS: {len(problem.rooms)}")
        self.stdout.write(f"  PERIODS: {len(problem.periods)}")
        self.stdout.write(f"  SLOTS: {len(problem.slots)}")
        self.stdout.write("")

        production_model = SolverModelBuilder().build(problem)
        production_proto = production_model.model.Proto()

        self.stdout.write("PRODUCTION MODEL")
        self.stdout.write(
            f"  VARIABLES: {len(production_proto.variables)}"
        )
        self.stdout.write(
            f"  CONSTRAINTS: {len(production_proto.constraints)}"
        )
        self.stdout.write("  HAS OBJECTIVE: TRUE")
        self.stdout.write("")

        # ================================================================
        # TEST 1 — EXACT PRODUCTION SOLVER
        # ================================================================

        production_solver = CPSATSolver()

        self.stdout.write("=" * 78)
        self.stdout.write("TEST 1 — EXACT PRODUCTION CPSATSOLVER")
        self.stdout.write("=" * 78)
        self.stdout.write(
            f"TIME LIMIT: {production_solver.time_limit_seconds}"
        )
        self.stdout.write(
            f"NUM WORKERS: {production_solver.num_workers}"
        )
        self.stdout.write("")

        production_result = production_solver.solve(
            problem=problem,
            solver_model=production_model,
        )

        production_statistics = production_result.statistics

        if production_statistics is not None:
            production_wall_time = (
                production_statistics.wall_time_seconds
            )
            production_branches = production_statistics.branches
            production_conflicts = production_statistics.conflicts
            production_objective = (
                production_statistics.objective_value
            )
        else:
            production_wall_time = None
            production_branches = None
            production_conflicts = None
            production_objective = None

        self.stdout.write("PRODUCTION RESULT")
        self.stdout.write(
            f"  STATUS: {production_result.status.value}"
        )
        self.stdout.write(
            f"  ASSIGNMENTS: {len(production_result.assignments)}"
        )
        self.stdout.write(
            f"  WALL TIME: {production_wall_time}"
        )
        self.stdout.write(
            f"  BRANCHES: {production_branches}"
        )
        self.stdout.write(
            f"  CONFLICTS: {production_conflicts}"
        )
        self.stdout.write(
            f"  OBJECTIVE: {production_objective}"
        )
        self.stdout.write(
            f"  ERROR: {production_result.error_message}"
        )
        self.stdout.write("")

        # ================================================================
        # TEST 2 — SAME MODEL, OBJECTIVE REMOVED FROM COPY
        # ================================================================

        self.stdout.write("=" * 78)
        self.stdout.write("TEST 2 — SAME MODEL WITHOUT OBJECTIVE")
        self.stdout.write("=" * 78)
        self.stdout.write(
            "Production model remains unchanged."
        )
        self.stdout.write(
            "No database objects are modified."
        )
        self.stdout.write("")

        no_objective_proto = copy.deepcopy(production_proto)
        no_objective_proto.ClearField("objective")

        no_objective_model = cp_model.CpModel()
        no_objective_model.Proto().CopyFrom(
            no_objective_proto
        )

        no_objective_solver = cp_model.CpSolver()
        no_objective_solver.parameters.max_time_in_seconds = (
            TIME_LIMIT_SECONDS
        )

        no_objective_started = datetime.now(timezone.utc)

        no_objective_status = no_objective_solver.solve(
            no_objective_model
        )

        no_objective_completed = datetime.now(timezone.utc)

        no_objective_result = {
            "status_code": int(no_objective_status),
            "status_name": no_objective_solver.status_name(
                no_objective_status
            ),
            "wall_time_seconds": float(
                no_objective_solver.wall_time
            ),
            "branches": int(
                no_objective_solver.num_branches
            ),
            "conflicts": int(
                no_objective_solver.num_conflicts
            ),
            "objective_value": None,
            "started_at": no_objective_started.isoformat(),
            "completed_at": no_objective_completed.isoformat(),
        }

        self.stdout.write("NO-OBJECTIVE RESULT")
        self.stdout.write(
            f"  STATUS: {no_objective_result['status_name']}"
        )
        self.stdout.write(
            f"  WALL TIME: "
            f"{no_objective_result['wall_time_seconds']}"
        )
        self.stdout.write(
            f"  BRANCHES: {no_objective_result['branches']}"
        )
        self.stdout.write(
            f"  CONFLICTS: {no_objective_result['conflicts']}"
        )
        self.stdout.write("")

        known_good_statistics = {}

        if known_good_run.statistics:
            try:
                known_good_statistics = json.loads(
                    known_good_run.statistics
                )
            except Exception:
                known_good_statistics = {
                    "raw": str(known_good_run.statistics)
                }

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "read_only": True,
            "database_mutation": False,
            "timetable_persistence": False,
            "term": {
                "id": str(term.id),
                "name": str(term),
            },
            "known_good_run": {
                "id": str(known_good_run.id),
                "status": known_good_run.status,
                "solver_status": known_good_run.solver_status,
                "objective_value": (
                    float(known_good_run.objective_value)
                    if known_good_run.objective_value is not None
                    else None
                ),
                "statistics": known_good_statistics,
            },
            "problem_dimensions": {
                "requirements": len(problem.lesson_requirements),
                "teachers": len(problem.teachers),
                "groups": len(problem.instructional_groups),
                "rooms": len(problem.rooms),
                "periods": len(problem.periods),
                "slots": len(problem.slots),
            },
            "production_model": {
                "variables": len(production_proto.variables),
                "constraints": len(production_proto.constraints),
                "has_objective": True,
            },
            "production_solver_configuration": {
                "class": (
                    f"{type(production_solver).__module__}."
                    f"{type(production_solver).__name__}"
                ),
                "time_limit_seconds": (
                    production_solver.time_limit_seconds
                ),
                "num_workers": production_solver.num_workers,
                "solve_source": inspect.getsource(
                    production_solver.solve
                ),
            },
            "production_result": {
                "status": production_result.status.value,
                "assignments": len(production_result.assignments),
                "wall_time_seconds": production_wall_time,
                "branches": production_branches,
                "conflicts": production_conflicts,
                "objective_value": production_objective,
                "error_message": production_result.error_message,
            },
            "no_objective_result": no_objective_result,
        }

        output_path.write_text(
            json.dumps(
                report,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        self.stdout.write("=" * 78)
        self.stdout.write("AUDIT RESULT")
        self.stdout.write("=" * 78)
        self.stdout.write(
            f"PRODUCTION STATUS: {production_result.status.value}"
        )
        self.stdout.write(
            "NO-OBJECTIVE STATUS: "
            f"{no_objective_result['status_name']}"
        )
        self.stdout.write(
            f"PRODUCTION ASSIGNMENTS: "
            f"{len(production_result.assignments)}"
        )
        self.stdout.write(f"PERSISTED: {output_path}")
        self.stdout.write("")
        self.stdout.write("NO DATABASE MUTATION PERFORMED.")
        self.stdout.write("NO TIMETABLE ENTRIES PERSISTED.")
        self.stdout.write("PRODUCTION MODEL WAS NOT MODIFIED.")
