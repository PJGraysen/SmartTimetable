from __future__ import annotations

import inspect

from django.core.management.base import BaseCommand

from apps.scheduling.models import SchedulingRun
from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)
from apps.scheduling.engine.solver.model import SolverModelBuilder


KNOWN_GOOD_RUN_ID = "8eccf5f8-c91a-439a-9970-297abfbdc403"


class Command(BaseCommand):
    help = "Inspect the exact OR-Tools objective wrapper used by production."

    def handle(self, *args, **options):
        self.stdout.write("=" * 78)
        self.stdout.write("SMARTTIMETABLE OR-TOOLS OBJECTIVE API AUDIT")
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: model build only")
        self.stdout.write("CP-SAT SOLVE: NO")
        self.stdout.write("DATABASE MUTATION: NO")
        self.stdout.write("")

        run = (
            SchedulingRun.objects
            .select_related("term")
            .get(id=KNOWN_GOOD_RUN_ID)
        )

        problem = DjangoSchedulingLoader().load_problem(
            term=run.term
        )

        solver_model = SolverModelBuilder().build(problem)
        proto = solver_model.model.Proto()
        objective = proto.objective

        self.stdout.write("MODEL")
        self.stdout.write(
            f"  VARIABLES: {len(proto.variables)}"
        )
        self.stdout.write(
            f"  CONSTRAINTS: {len(proto.constraints)}"
        )
        self.stdout.write("")

        self.stdout.write("OBJECTIVE RUNTIME TYPE")
        self.stdout.write(
            f"  TYPE: {type(objective)}"
        )
        self.stdout.write(
            f"  MODULE: {type(objective).__module__}"
        )
        self.stdout.write(
            f"  CLASS: {type(objective).__name__}"
        )
        self.stdout.write("")

        self.stdout.write("OBJECTIVE ATTRIBUTES")
        for name in sorted(dir(objective)):
            if not name.startswith("_"):
                try:
                    value = getattr(objective, name)
                    if callable(value):
                        self.stdout.write(
                            f"  {name}: <callable>"
                        )
                    else:
                        self.stdout.write(
                            f"  {name}: {value!r}"
                        )
                except Exception as exc:
                    self.stdout.write(
                        f"  {name}: <ERROR {exc}>"
                    )

        self.stdout.write("")
        self.stdout.write("OBJECTIVE PROPERTIES")
        for name in (
            "vars",
            "coeffs",
            "offset",
            "scaling_factor",
            "domain",
        ):
            try:
                value = getattr(objective, name)
                self.stdout.write(
                    f"  {name}: type={type(value)} value={value!r}"
                )
            except Exception as exc:
                self.stdout.write(
                    f"  {name}: UNAVAILABLE ({exc})"
                )

        self.stdout.write("")
        self.stdout.write("CP MODEL PROTO OBJECTIVE")
        self.stdout.write(
            f"  TYPE: {type(proto.objective)}"
        )

        self.stdout.write("")
        self.stdout.write("SUPPORTED MODEL METHODS")
        for name in sorted(dir(solver_model.model)):
            if name.startswith("_"):
                continue

            lowered = name.lower()

            if (
                "objective" in lowered
                or "minimiz" in lowered
                or "maximiz" in lowered
                or "proto" in lowered
            ):
                try:
                    value = getattr(solver_model.model, name)
                    self.stdout.write(
                        f"  {name}: "
                        f"{'<callable>' if callable(value) else repr(value)}"
                    )
                except Exception as exc:
                    self.stdout.write(
                        f"  {name}: <ERROR {exc}>"
                    )

        self.stdout.write("")
        self.stdout.write("OBJECTIVE SOURCE")
        try:
            self.stdout.write(
                inspect.getsource(
                    type(solver_model.model).Minimize
                )
            )
        except Exception as exc:
            self.stdout.write(
                f"  Source unavailable: {exc}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("AUDIT COMPLETE — NO SOLVE EXECUTED")
        self.stdout.write("=" * 78)
