from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)


AUDIT_DIR = (
    Path(__file__).resolve().parents[4]
    / ".smarttimetable-audits"
    / "production-model-fingerprints"
)

LATEST_JSON = AUDIT_DIR / "latest.json"


def stable_value(value: Any, depth: int = 0) -> Any:
    """
    Convert the actual production SolverModel object into a deterministic,
    JSON-compatible structural representation.

    This deliberately does NOT assume that SolverModel has .proto,
    SerializeToString(), or protobuf DESCRIPTOR support.
    """
    if depth > 12:
        return f"<MAX_DEPTH:{type(value).__name__}>"

    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, bytes):
        return {
            "__type__": "bytes",
            "sha256": hashlib.sha256(value).hexdigest(),
            "length": len(value),
        }

    if isinstance(value, (list, tuple)):
        return [
            stable_value(item, depth + 1)
            for item in value
        ]

    if isinstance(value, set):
        values = [
            stable_value(item, depth + 1)
            for item in value
        ]
        return sorted(
            values,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                default=str,
            ),
        )

    if isinstance(value, dict):
        return {
            str(key): stable_value(item, depth + 1)
            for key, item in sorted(
                value.items(),
                key=lambda item: str(item[0]),
            )
        }

    # Dataclass-like / ordinary Python objects.
    if hasattr(value, "__dict__"):
        result = {
            "__type__": (
                f"{type(value).__module__}."
                f"{type(value).__qualname__}"
            )
        }

        for name in sorted(vars(value)):
            if name.startswith("__"):
                continue

            try:
                attribute = getattr(value, name)
                result[name] = stable_value(
                    attribute,
                    depth + 1,
                )
            except Exception as exc:
                result[name] = (
                    f"<UNREADABLE:{type(exc).__name__}>"
                )

        return result

    # OR-Tools wrapper objects and other extension objects may not expose
    # __dict__. Preserve their type and deterministic textual form.
    try:
        text = str(value)
    except Exception:
        text = repr(value)

    return {
        "__type__": (
            f"{type(value).__module__}."
            f"{type(value).__qualname__}"
        ),
        "__text__": text,
    }


def sha256_json(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def safe_len(value: Any) -> int | None:
    try:
        return len(value)
    except (TypeError, AttributeError):
        return None


class Command(BaseCommand):
    help = (
        "Build the exact production SolverModel and persist a "
        "read-only structural fingerprint."
    )

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("SMARTTIMETABLE PRODUCTION MODEL FINGERPRINT")
        self.stdout.write("=" * 78)
        self.stdout.write(
            "READ-ONLY: model construction only; no solve; no DB writes"
        )
        self.stdout.write("")

        try:
            from apps.scheduling.models import Term
        except ImportError as exc:
            raise CommandError(
                f"Unable to import Term: {exc}"
            ) from exc

        term = Term.objects.order_by("-id").first()

        if term is None:
            raise CommandError("No Term exists in the database.")

        self.stdout.write(
            f"TERM: {term.id} | {term}"
        )

        loader = DjangoSchedulingLoader()
        problem = loader.load_problem(term=term)

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
        self.stdout.write(
            f"TEACHER ASSIGNMENTS: {len(problem.teacher_assignments)}"
        )
        self.stdout.write(
            f"TEACHER AVAILABILITY: {len(problem.teacher_availability)}"
        )
        self.stdout.write(
            f"FREE AFTERNOONS: {len(problem.teacher_free_afternoons)}"
        )
        self.stdout.write(
            f"ROOM AVAILABILITY: {len(problem.room_availability)}"
        )
        self.stdout.write("")

        from apps.scheduling.engine.solver.model import SolverModelBuilder

        # Exact production API established from the profiler:
        # SolverModelBuilder().build(problem)
        builder = SolverModelBuilder()
        model = builder.build(problem)

        model_type = (
            f"{type(model).__module__}."
            f"{type(model).__qualname__}"
        )

        self.stdout.write(
            f"SOLVER MODEL TYPE: {model_type}"
        )

        # Discover actual public structure without assuming .proto.
        public_attributes = sorted(
            name
            for name in dir(model)
            if not name.startswith("_")
        )

        self.stdout.write(
            "PUBLIC MODEL ATTRIBUTES:"
        )

        for name in public_attributes:
            try:
                value = getattr(model, name)

                if callable(value):
                    description = "<callable>"
                else:
                    length = safe_len(value)
                    if length is not None:
                        description = (
                            f"<{type(value).__name__}; len={length}>"
                        )
                    else:
                        description = (
                            f"<{type(value).__name__}>"
                        )

                self.stdout.write(
                    f"  {name}: {description}"
                )
            except Exception as exc:
                self.stdout.write(
                    f"  {name}: <ERROR {type(exc).__name__}>"
                )

        self.stdout.write("")

        # Fingerprint the actual model object's structural state.
        structural_model = stable_value(model)

        fingerprint = sha256_json(
            {
                "model_type": model_type,
                "model": structural_model,
            }
        )

        # These are obtained from the same public structure used by the
        # production model profiler. We deliberately do not require .proto.
        variables = None
        constraints = None
        has_objective = None

        for candidate in (
            "variables",
            "assignment_variables",
            "assignment_variable",
        ):
            if hasattr(model, candidate):
                value = getattr(model, candidate)
                length = safe_len(value)
                if length is not None:
                    variables = length
                    break

        for candidate in (
            "constraints",
            "model",
        ):
            if hasattr(model, candidate):
                value = getattr(model, candidate)
                length = safe_len(value)
                if length is not None:
                    constraints = length
                    break

        if hasattr(model, "objective"):
            objective = getattr(model, "objective")
            has_objective = bool(objective)

        result = {
            "term_id": str(term.id),
            "term": str(term),
            "requirements": len(problem.lesson_requirements),
            "teachers": len(problem.teachers),
            "instructional_groups": len(problem.instructional_groups),
            "rooms": len(problem.rooms),
            "periods": len(problem.periods),
            "slots": len(problem.slots),
            "teacher_assignments": len(problem.teacher_assignments),
            "teacher_availability": len(problem.teacher_availability),
            "teacher_free_afternoons": len(
                problem.teacher_free_afternoons
            ),
            "room_availability": len(problem.room_availability),
            "solver_model_type": model_type,
            "detected_variables": variables,
            "detected_constraints": constraints,
            "detected_has_objective": has_objective,
            "fingerprint_algorithm": (
                "sha256(canonical JSON structural representation "
                "of actual SolverModel)"
            ),
            "fingerprint": fingerprint,
            "public_model_attributes": public_attributes,
        }

        AUDIT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        LATEST_JSON.write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                default=str,
            ),
            encoding="utf-8",
        )

        # Also persist the complete structural representation so that
        # future comparisons can identify exactly what changed.
        structural_path = AUDIT_DIR / "latest_structure.json"

        structural_path.write_text(
            json.dumps(
                {
                    "model_type": model_type,
                    "model": structural_model,
                },
                indent=2,
                sort_keys=True,
                default=str,
            ),
            encoding="utf-8",
        )

        self.stdout.write("")
        self.stdout.write("MODEL FINGERPRINT")
        self.stdout.write(
            f"  FINGERPRINT: {fingerprint}"
        )

        if variables is not None:
            self.stdout.write(
                f"  DETECTED VARIABLES: {variables}"
            )

        if constraints is not None:
            self.stdout.write(
                f"  DETECTED CONSTRAINTS: {constraints}"
            )

        if has_objective is not None:
            self.stdout.write(
                f"  DETECTED OBJECTIVE: {has_objective}"
            )

        self.stdout.write("")
        self.stdout.write(
            f"PERSISTED SUMMARY: {LATEST_JSON}"
        )
        self.stdout.write(
            f"PERSISTED STRUCTURE: {structural_path}"
        )
        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("FINGERPRINT COMPLETE")
        self.stdout.write("=" * 78)
        self.stdout.write("")
