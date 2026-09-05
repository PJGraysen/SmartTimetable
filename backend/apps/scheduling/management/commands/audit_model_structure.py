from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)


AUDIT_DIR = (
    Path(__file__).resolve().parents[4]
    / ".smarttimetable-audits"
    / "model-structure"
)

OUTPUT = AUDIT_DIR / "latest.json"


def stable_text(value: Any) -> str:
    try:
        return str(value)
    except Exception:
        return repr(value)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        stable_text(value).encode("utf-8")
    ).hexdigest()


def safe_len(value: Any) -> int | None:
    try:
        return len(value)
    except (TypeError, AttributeError):
        return None


def proto_constraint_summary(cp_model: Any) -> dict[str, Any]:
    """
    Inspect the actual CpModel exposed by SolverModel.model.

    This deliberately uses the public CpModel API already established
    by the production model rather than assuming a protobuf wrapper.
    """
    result: dict[str, Any] = {}

    proto = None

    # OR-Tools CpModel normally exposes proto through Proto().
    proto_method = getattr(cp_model, "Proto", None)

    if callable(proto_method):
        try:
            proto = proto_method()
        except Exception as exc:
            result["proto_error"] = type(exc).__name__

    if proto is None:
        result["proto_available"] = False
        return result

    result["proto_available"] = True
    result["proto_type"] = (
        f"{type(proto).__module__}."
        f"{type(proto).__qualname__}"
    )

    variables = getattr(proto, "variables", None)
    constraints = getattr(proto, "constraints", None)

    result["variables"] = safe_len(variables)
    result["constraints"] = safe_len(constraints)

    constraint_types: Counter[str] = Counter()

    if constraints is not None:
        for constraint in constraints:
            try:
                which = constraint.WhichOneof("constraint")
                constraint_types[str(which)] += 1
            except Exception:
                constraint_types["<unknown>"] += 1

    result["constraint_types"] = dict(
        sorted(constraint_types.items())
    )

    try:
        result["has_objective"] = bool(proto.objective)
    except Exception:
        result["has_objective"] = None

    return result


class Command(BaseCommand):
    help = (
        "Persist a read-only structural audit of the exact production "
        "CP-SAT model."
    )

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("SMARTTIMETABLE MODEL STRUCTURE AUDIT")
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: no solve and no database mutation")
        self.stdout.write("")

        from apps.scheduling.models import Term

        term = Term.objects.order_by("-id").first()

        if term is None:
            raise CommandError("No active Term exists.")

        loader = DjangoSchedulingLoader()
        problem = loader.load_problem(term=term)

        from apps.scheduling.engine.solver.model import SolverModelBuilder

        builder = SolverModelBuilder()
        solver_model = builder.build(problem)

        self.stdout.write(
            "ACTUAL SOLVER MODEL:"
        )
        self.stdout.write(
            f"  TYPE: {type(solver_model).__module__}."
            f"{type(solver_model).__qualname__}"
        )

        cp_model = solver_model.model

        self.stdout.write(
            f"  CP MODEL TYPE: {type(cp_model).__module__}."
            f"{type(cp_model).__qualname__}"
        )

        variables = solver_model.variables

        self.stdout.write(
            f"  ASSIGNMENT VARIABLES: {len(variables)}"
        )

        self.stdout.write("")

        summary = proto_constraint_summary(cp_model)

        self.stdout.write("CP-SAT MODEL STRUCTURE:")

        for key, value in summary.items():
            if key == "constraint_types":
                continue

            self.stdout.write(
                f"  {key.upper()}: {value}"
            )

        self.stdout.write("")
        self.stdout.write("CONSTRAINT TYPES:")

        for name, count in summary.get(
            "constraint_types",
            {}
        ).items():
            self.stdout.write(
                f"  {name}: {count}"
            )

        # Fingerprint the actual CP-SAT proto textual representation.
        #
        # We do NOT call SerializeToString() or MessageToJson() because
        # this environment exposes the underlying object through the
        # OR-Tools wrapper.
        try:
            proto_text = stable_text(
                cp_model.Proto()
            )
        except Exception:
            proto_text = stable_text(cp_model)

        model_fingerprint = fingerprint(
            proto_text
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
                "teacher_assignments": len(
                    problem.teacher_assignments
                ),
                "teacher_availability": len(
                    problem.teacher_availability
                ),
                "teacher_free_afternoons": len(
                    problem.teacher_free_afternoons
                ),
                "room_availability": len(
                    problem.room_availability
                ),
            },
            "solver_model": {
                "type": (
                    f"{type(solver_model).__module__}."
                    f"{type(solver_model).__qualname__}"
                ),
                "assignment_variables": len(variables),
                "fingerprint": model_fingerprint,
            },
            "cp_sat_model": summary,
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

        self.stdout.write("")
        self.stdout.write(
            f"MODEL FINGERPRINT: {model_fingerprint}"
        )
        self.stdout.write(
            f"PERSISTED: {OUTPUT}"
        )

        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("MODEL STRUCTURE AUDIT COMPLETE")
        self.stdout.write("=" * 78)
        self.stdout.write("")
