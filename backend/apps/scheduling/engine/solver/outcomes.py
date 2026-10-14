"""Translate a failed SolverResult into a user-safe failure report."""
from __future__ import annotations

from dataclasses import dataclass

from apps.scheduling.engine.domain.enums import SolverStatus
from apps.scheduling.engine.solver.result import SolverResult


@dataclass(frozen=True, slots=True)
class FailureReport:
    """Structured, user-safe summary of a failed generation attempt."""

    code: str
    user_message: str
    technical_detail: str
    hints: tuple[str, ...] = ()

    def to_payload(self) -> dict:
        return {
            "code": self.code,
            "message": self.user_message,
            "hints": list(self.hints),
        }


_ASSUMPTION_HINTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "block:": (
        "BLOCK_SYNCHRONIZATION",
        (
            "Check that every subject in the block has the same weekly lesson quota.",
            "Verify that paired streams (e.g. 4E / 4W) are both active for the term.",
            "Confirm the block's authoritative day/lesson slots are still correct.",
        ),
    ),
    "sci_adjacent:": (
        "SCIENCE_ADJACENCY",
        (
            "Relax the 'no two sciences adjacent' rule for the affected class(es).",
            "Free a science teacher, or move a science period to a lighter day.",
        ),
    ),
    "complex_adjacent:": (
        "SCIENCE_ADJACENCY",
        (
            "Relax the 'no science-or-maths adjacent' rule for the affected "
            "class on that day.",
            "Redistribute the affected subject to a different day or a "
            "non-adjacent period.",
        ),
    ),
    "teacher_avail:": (
        "TEACHER_AVAILABILITY",
        (
            "Check teacher unavailability on the affected day/period.",
            "Consider adding a support teacher for the affected slot.",
        ),
    ),
}


_DEFAULT_INFEASIBLE_HINTS: tuple[str, ...] = (
    "Inspect the scheduling-run diagnostics for the classes, teachers, or subjects named in the report.",
    "Relax a hard rule (block synchronization, science adjacency) for one or more classes and retry.",
    "If the problem persists, contact the timetabling administrator.",
)


def _classify_assumption(name: str) -> tuple[str, tuple[str, ...]] | None:
    for prefix, payload in _ASSUMPTION_HINTS.items():
        if name.startswith(prefix):
            return payload
    return None


def _derive_infeasible_hints(unsat_core_names: tuple[str, ...]) -> tuple[str, ...]:
    if not unsat_core_names:
        return _DEFAULT_INFEASIBLE_HINTS
    seen: list[str] = []
    for name in unsat_core_names:
        classified = _classify_assumption(name)
        if classified is None:
            continue
        _, hints = classified
        for hint in hints:
            if hint not in seen:
                seen.append(hint)
    return tuple(seen) if seen else _DEFAULT_INFEASIBLE_HINTS


def describe_failure(
    result: SolverResult,
    *,
    unsat_core_names: tuple[str, ...] = (),
) -> FailureReport:
    """Translate a failed SolverResult into a FailureReport."""
    technical = result.error_message or ""
    status = result.status

    if status == SolverStatus.INFEASIBLE:
        return FailureReport(
            code="INFEASIBLE",
            user_message=(
                "No valid timetable exists under the current rules and staffing. "
                "The scheduler cannot produce a clash-free schedule with the "
                "constraints that are currently hard."
            ),
            technical_detail=technical,
            hints=_derive_infeasible_hints(unsat_core_names),
        )

    if status == SolverStatus.MODEL_INVALID:
        return FailureReport(
            code="MODEL_INVALID",
            user_message=(
                "The scheduling model is malformed and cannot be solved. "
                "This is a configuration problem, not a data problem - "
                "contact the timetabling administrator."
            ),
            technical_detail=technical,
            hints=(
                "Recheck the latest contract changes (blocks, streams, teacher availability).",
            ),
        )

    if status == SolverStatus.UNKNOWN:
        return FailureReport(
            code="TIMEOUT",
            user_message=(
                "The scheduler ran out of time before finding a solution. "
                "The current rules may be too tight to solve quickly."
            ),
            technical_detail=technical,
            hints=(
                "Increase the solver time limit and retry.",
                "Relax a hard rule to shrink the search space.",
            ),
        )

    return FailureReport(
        code="SOLVER_FAILURE",
        user_message=(
            "Timetable generation failed before a schedule could be produced. "
            "The technical detail has been logged for the administrator."
        ),
        technical_detail=technical,
        hints=_DEFAULT_INFEASIBLE_HINTS,
    )
