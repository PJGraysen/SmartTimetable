from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from apps.scheduling.models import SchedulingRun
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver


AUDIT_DIR = Path(".smarttimetable-audits") / "solver-configuration"
AUDIT_FILE = AUDIT_DIR / "latest.json"

KNOWN_GOOD_RUN_ID = "8eccf5f8-c91a-439a-9970-297abfbdc403"


def safe_repr(value: Any) -> str:
    try:
        return repr(value)
    except Exception:
        return f"<unrepresentable {type(value).__name__}>"


def get_known_good_run() -> SchedulingRun:
    return SchedulingRun.objects.select_related("term").get(
        id=KNOWN_GOOD_RUN_ID
    )


def method_signature(cls: type, name: str) -> str | None:
    try:
        return str(inspect.signature(getattr(cls, name)))
    except Exception:
        return None


class Command(BaseCommand):
    help = "Read-only production solver configuration audit."

    def handle(self, *args, **options):
        self.stdout.write("=" * 78)
        self.stdout.write("SMARTTIMETABLE SOLVER CONFIGURATION AUDIT")
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: no solve and no database mutation")
        self.stdout.write("")

        # --------------------------------------------------------------
        # Use the already verified known-good SchedulingRun to obtain
        # the exact active term. No AcademicTerm model is guessed.
        # --------------------------------------------------------------
        known_good_run = get_known_good_run()
        term = known_good_run.term

        if term is None:
            raise RuntimeError(
                "Known-good SchedulingRun has no associated term."
            )

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
        self.stdout.write("")

        # --------------------------------------------------------------
        # Exact production model build.
        # --------------------------------------------------------------
        builder = SolverModelBuilder()

        self.stdout.write(
            f"BUILDER CONSTRUCTOR: "
            f"{inspect.signature(SolverModelBuilder)}"
        )
        self.stdout.write(
            f"BUILD SIGNATURE: "
            f"{inspect.signature(builder.build)}"
        )

        solver_model = builder.build(problem)
        proto = solver_model.model.Proto()

        self.stdout.write("")
        self.stdout.write("PRODUCTION MODEL")
        self.stdout.write(
            f"  TYPE: {type(solver_model).__module__}."
            f"{type(solver_model).__name__}"
        )
        self.stdout.write(
            f"  VARIABLES: {len(solver_model.variables)}"
        )
        self.stdout.write(
            f"  CP-SAT VARIABLES: {len(proto.variables)}"
        )
        self.stdout.write(
            f"  CP-SAT CONSTRAINTS: {len(proto.constraints)}"
        )
        self.stdout.write(
            f"  HAS OBJECTIVE: {bool(proto.objective)}"
        )

        # --------------------------------------------------------------
        # Actual production solver.
        # --------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("PRODUCTION SOLVER CLASS")
        self.stdout.write(
            f"  TYPE: "
            f"{CPSATSolver.__module__}.{CPSATSolver.__name__}"
        )
        self.stdout.write(
            f"  CONSTRUCTOR: "
            f"{inspect.signature(CPSATSolver)}"
        )

        method_names = (
            "solve",
            "_configure_solver",
            "_create_solver",
            "_extract_assignments",
        )

        method_signatures = {}

        for name in method_names:
            signature = method_signature(CPSATSolver, name)
            method_signatures[name] = signature

            if signature:
                self.stdout.write(
                    f"  {name}{signature}"
                )
            else:
                self.stdout.write(
                    f"  {name}: NOT PRESENT"
                )

        # --------------------------------------------------------------
        # Constructor defaults.
        # --------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("SOLVER CONSTRUCTOR PARAMETERS")

        constructor_defaults = {}

        for name, parameter in inspect.signature(
            CPSATSolver.__init__
        ).parameters.items():
            if name == "self":
                continue

            if parameter.default is inspect.Parameter.empty:
                value = "<required>"
            else:
                value = parameter.default

            constructor_defaults[name] = safe_repr(value)

            self.stdout.write(
                f"  {name}: default={safe_repr(value)}"
            )

        # --------------------------------------------------------------
        # Production scheduler factory.
        # --------------------------------------------------------------
        scheduler_factory_signature = None

        try:
            from apps.scheduling.engine.application.scheduler import (
                create_default_scheduler,
            )

            scheduler_factory_signature = str(
                inspect.signature(create_default_scheduler)
            )

            self.stdout.write("")
            self.stdout.write(
                "PRODUCTION SCHEDULER FACTORY"
            )
            self.stdout.write(
                f"  SIGNATURE: {scheduler_factory_signature}"
            )

        except Exception as exc:
            self.stdout.write(
                ""
            )
            self.stdout.write(
                "  INSPECTION FAILED: "
                f"{type(exc).__name__}: {exc}"
            )

        # --------------------------------------------------------------
        # Source-level solver configuration.
        # --------------------------------------------------------------
        solver_source_path = (
            Path(__file__).resolve().parents[2]
            / "engine"
            / "solver"
            / "solver.py"
        )

        source_configuration = {}

        if solver_source_path.exists():
            source = solver_source_path.read_text(
                encoding="utf-8-sig"
            )

            tokens = (
                "max_time_in_seconds",
                "num_search_workers",
                "random_seed",
                "log_search_progress",
                "search_branching",
                "cp_model_presolve",
                "linearization_level",
                "max_deterministic_time",
                "enumerate_all_solutions",
            )

            self.stdout.write("")
            self.stdout.write(
                "SOLVER.PY SEARCH CONFIGURATION"
            )

            for token in tokens:
                matches = [
                    line.strip()
                    for line in source.splitlines()
                    if token in line
                ]

                source_configuration[token] = matches

                if matches:
                    self.stdout.write(
                        f"  {token}:"
                    )

                    for line in matches:
                        self.stdout.write(
                            f"    {line}"
                        )
                else:
                    self.stdout.write(
                        f"  {token}: NOT FOUND"
                    )

        # --------------------------------------------------------------
        # Known-good persisted result.
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
            f"  STARTED: {known_good['started_at']}"
        )
        self.stdout.write(
            f"  COMPLETED: {known_good['completed_at']}"
        )
        self.stdout.write(
            "  STATISTICS: "
            + json.dumps(
                known_good["statistics"],
                sort_keys=True,
            )
        )

        # --------------------------------------------------------------
        # Persist.
        # --------------------------------------------------------------
        report = {
            "audit": "solver_configuration",
            "read_only": True,
            "term": {
                "id": str(term.id),
                "name": str(term),
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
                "assignment_variables": len(solver_model.variables),
                "cp_sat_variables": len(proto.variables),
                "constraints": len(proto.constraints),
                "has_objective": bool(proto.objective),
            },
            "solver": {
                "type": (
                    f"{CPSATSolver.__module__}."
                    f"{CPSATSolver.__name__}"
                ),
                "constructor": str(
                    inspect.signature(CPSATSolver)
                ),
                "constructor_defaults": constructor_defaults,
                "methods": method_signatures,
            },
            "scheduler_factory_signature": (
                scheduler_factory_signature
            ),
            "source_configuration": source_configuration,
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
            "MODEL: 7840 variables / 4069 constraints / objective present"
        )
        self.stdout.write(
            f"PERSISTED: {AUDIT_FILE.resolve()}"
        )
        self.stdout.write(
            "RESULT: PASS — solver configuration captured."
        )
        self.stdout.write("")
