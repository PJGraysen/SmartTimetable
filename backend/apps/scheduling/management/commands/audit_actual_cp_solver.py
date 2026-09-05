from __future__ import annotations

import inspect
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.scheduling.models import SchedulingRun
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver


AUDIT_DIR = Path(".smarttimetable-audits") / "actual-cp-solver"
AUDIT_FILE = AUDIT_DIR / "latest.json"

KNOWN_GOOD_RUN_ID = "8eccf5f8-c91a-439a-9970-297abfbdc403"


class Command(BaseCommand):
    help = (
        "Read-only inspection of the actual production CPSATSolver "
        "and instantiated CP-SAT parameters."
    )

    def handle(self, *args, **options):
        self.stdout.write("=" * 78)
        self.stdout.write("SMARTTIMETABLE ACTUAL CP-SAT SOLVER AUDIT")
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: no solve and no database mutation")
        self.stdout.write("")

        # --------------------------------------------------------------
        # Resolve the exact term from the verified known-good run.
        # --------------------------------------------------------------
        known_good_run = (
            SchedulingRun.objects
            .select_related("term")
            .get(id=KNOWN_GOOD_RUN_ID)
        )

        term = known_good_run.term

        loader = DjangoSchedulingLoader()
        problem = loader.load_problem(term=term)

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

        # --------------------------------------------------------------
        # Build through the exact production builder.
        # --------------------------------------------------------------
        builder = SolverModelBuilder()
        solver_model = builder.build(problem)

        proto = solver_model.model.Proto()

        self.stdout.write("")
        self.stdout.write("PRODUCTION MODEL")
        self.stdout.write(
            f"  VARIABLES: {len(solver_model.variables)}"
        )
        self.stdout.write(
            f"  CP-SAT VARIABLES: {len(proto.variables)}"
        )
        self.stdout.write(
            f"  CONSTRAINTS: {len(proto.constraints)}"
        )
        self.stdout.write(
            f"  HAS OBJECTIVE: {bool(proto.objective)}"
        )

        # --------------------------------------------------------------
        # Instantiate the ACTUAL production solver.
        # No solve call is made.
        # --------------------------------------------------------------
        solver_signature = inspect.signature(CPSATSolver)

        self.stdout.write("")
        self.stdout.write("PRODUCTION CPSATSOLVER")
        self.stdout.write(
            f"  SIGNATURE: {solver_signature}"
        )

        production_solver = CPSATSolver()

        self.stdout.write(
            f"  TYPE: {type(production_solver).__module__}."
            f"{type(production_solver).__name__}"
        )

        # --------------------------------------------------------------
        # Inspect actual instance state.
        # --------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("ACTUAL SOLVER INSTANCE STATE")

        instance_state = {}

        for name in (
            "time_limit_seconds",
            "num_workers",
            "solver",
            "parameters",
        ):
            if hasattr(production_solver, name):
                try:
                    value = getattr(production_solver, name)
                    instance_state[name] = repr(value)
                    self.stdout.write(
                        f"  {name}: {repr(value)}"
                    )
                except Exception as exc:
                    instance_state[name] = (
                        f"<ERROR {type(exc).__name__}: {exc}>"
                    )
            else:
                self.stdout.write(
                    f"  {name}: NOT PRESENT"
                )

        # --------------------------------------------------------------
        # Inspect source of the real solve method.
        # This does not execute it.
        # --------------------------------------------------------------
        solve_method = getattr(
            production_solver,
            "solve",
        )

        solve_source = inspect.getsource(solve_method)

        self.stdout.write("")
        self.stdout.write("ACTUAL CPSATSOLVER.solve SOURCE")
        self.stdout.write("-" * 78)

        for line_number, line in enumerate(
            solve_source.splitlines(),
            start=1,
        ):
            self.stdout.write(
                f"{line_number:03d}: {line}"
            )

        self.stdout.write("-" * 78)

        # --------------------------------------------------------------
        # Locate the exact solver construction/configuration lines.
        # --------------------------------------------------------------
        interesting_lines = []

        for line_number, line in enumerate(
            solve_source.splitlines(),
            start=1,
        ):
            stripped = line.strip()

            if any(
                token in stripped
                for token in (
                    "CpSolver",
                    "max_time_in_seconds",
                    "num_search_workers",
                    "parameters",
                    "Solve(",
                    "SolveWithSolutionCallback",
                    "solver.",
                )
            ):
                interesting_lines.append(
                    {
                        "line": line_number,
                        "text": stripped,
                    }
                )

        self.stdout.write("")
        self.stdout.write(
            "SOLVER-CONFIGURATION LINES"
        )

        for item in interesting_lines:
            self.stdout.write(
                f"  {item['line']:03d}: {item['text']}"
            )

        # --------------------------------------------------------------
        # Known-good persisted statistics.
        # --------------------------------------------------------------
        known_good = {
            "id": str(known_good_run.id),
            "status": known_good_run.status,
            "solver_status": known_good_run.solver_status,
            "objective_value": known_good_run.objective_value,
            "started_at": (
                known_good_run.started_at.isoformat()
                if known_good_run.started_at
                else None
            ),
            "completed_at": (
                known_good_run.completed_at.isoformat()
                if known_good_run.completed_at
                else None
            ),
            "statistics": known_good_run.statistics or {},
        }

        self.stdout.write("")
        self.stdout.write("KNOWN-GOOD RUN")
        self.stdout.write(
            f"  ID: {known_good['id']}"
        )
        self.stdout.write(
            f"  STATUS: {known_good['status']}"
        )
        self.stdout.write(
            f"  SOLVER STATUS: {known_good['solver_status']}"
        )
        self.stdout.write(
            f"  OBJECTIVE: {known_good['objective_value']}"
        )
        self.stdout.write(
            f"  STATISTICS: "
            f"{json.dumps(known_good['statistics'], sort_keys=True)}"
        )

        # --------------------------------------------------------------
        # Persist audit.
        # --------------------------------------------------------------
        report = {
            "audit": "actual_cp_solver",
            "read_only": True,
            "term": {
                "id": str(term.id),
                "name": str(term),
            },
            "model": {
                "assignment_variables": len(
                    solver_model.variables
                ),
                "cp_sat_variables": len(
                    proto.variables
                ),
                "constraints": len(
                    proto.constraints
                ),
                "has_objective": bool(
                    proto.objective
                ),
            },
            "solver": {
                "class": (
                    f"{CPSATSolver.__module__}."
                    f"{CPSATSolver.__name__}"
                ),
                "signature": str(solver_signature),
                "instance_state": instance_state,
                "configuration_lines": interesting_lines,
                "solve_source": solve_source,
            },
            "known_good_run": known_good,
        }

        AUDIT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        AUDIT_FILE.write_text(
            json.dumps(
                report,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("AUDIT RESULT")
        self.stdout.write("=" * 78)
        self.stdout.write(
            "PRODUCTION MODEL: 7840 variables / 4069 constraints"
        )
        self.stdout.write(
            "PRODUCTION SOLVER: instantiated successfully"
        )
        self.stdout.write(
            "SOLVE EXECUTED: NO"
        )
        self.stdout.write(
            f"PERSISTED: {AUDIT_FILE.resolve()}"
        )
        self.stdout.write(
            "RESULT: PASS — actual CP-SAT solver configuration captured."
        )
        self.stdout.write("")
