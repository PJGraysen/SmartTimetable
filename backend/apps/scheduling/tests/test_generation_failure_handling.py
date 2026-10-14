"""Focused tests for the failure-report and unsat-core plumbing."""
from __future__ import annotations

from apps.scheduling.engine.domain.enums import SolverStatus
from apps.scheduling.engine.solver.outcomes import describe_failure
from apps.scheduling.engine.solver.result import SolverResult


def _make_result(status, message=""):
    return SolverResult(status=status, error_message=message or None)


def test_infeasible_with_block_core_surfaces_block_hint():
    report = describe_failure(
        _make_result(SolverStatus.INFEASIBLE, "cp-sat: infeasible"),
        unsat_core_names=("block:OPTION_1:g-uuid:MON:p-uuid:r-uuid",),
    )
    assert report.code == "INFEASIBLE"
    assert "no valid timetable" in report.user_message.lower()
    joined = " ".join(report.hints).lower()
    assert "block" in joined


def test_infeasible_with_no_core_falls_back_to_default_hints():
    report = describe_failure(
        _make_result(SolverStatus.INFEASIBLE, "cp-sat: infeasible"),
        unsat_core_names=(),
    )
    assert report.code == "INFEASIBLE"
    assert report.hints


def test_model_invalid_is_marked_as_configuration_problem():
    report = describe_failure(
        _make_result(SolverStatus.MODEL_INVALID, "bad literal"),
    )
    assert report.code == "MODEL_INVALID"
    assert "configuration" in report.user_message.lower()


def test_unknown_is_reported_as_timeout():
    report = describe_failure(
        _make_result(SolverStatus.UNKNOWN, "search limit"),
    )
    assert report.code == "TIMEOUT"
    assert "time" in report.user_message.lower()


def test_failed_falls_through_to_solver_failure():
    report = describe_failure(
        _make_result(SolverStatus.FAILED, "boom"),
    )
    assert report.code == "SOLVER_FAILURE"
    assert report.technical_detail == "boom"


def test_complex_adjacent_prefix_routes_to_science_adjacency_hint():
    from apps.scheduling.engine.solver.outcomes import _classify_assumption

    classified = _classify_assumption(
        "complex_adjacent:g-uuid:WED:3:4:BIO-MAT"
    )
    assert classified is not None
    code, hints = classified
    assert code == "SCIENCE_ADJACENCY"
    assert any("science" in h.lower() or "maths" in h.lower() for h in hints)


def test_solver_model_exposes_complex_adjacency_method():
    from apps.scheduling.engine.solver.model import SolverModelBuilder

    assert hasattr(
        SolverModelBuilder, "_add_complex_adjacency_constraints"
    )


def test_solver_model_carries_assumption_names_field():
    from dataclasses import fields
    from apps.scheduling.engine.solver.model import SolverModel

    names = {f.name for f in fields(SolverModel)}
    assert "assumption_names" in names


def test_persistence_service_exposes_gst_filler():
    from apps.scheduling.engine.application.timetable_persistence import (
        TimetablePersistenceService,
    )

    assert hasattr(TimetablePersistenceService, "_inject_gst_filler")


def test_persistence_helper_returns_false_for_unrelated_exception():
    from apps.scheduling.api.views import SchedulingRunExecuteView

    try:
        raise RuntimeError("plain error")
    except RuntimeError as exc:
        assert not SchedulingRunExecuteView._looks_like_persistence_failure(
            exc
        )


def test_persistence_helper_detects_persistence_origin_via_module():
    from apps.scheduling.api.views import SchedulingRunExecuteView

    class PersistenceError(Exception):
        pass

    PersistenceError.__module__ = (
        "apps.scheduling.engine.application.timetable_persistence"
    )

    try:
        raise PersistenceError("save failed")
    except PersistenceError as exc:
        assert SchedulingRunExecuteView._looks_like_persistence_failure(exc)


def test_persistence_failure_report_has_distinct_code():
    from apps.scheduling.engine.solver.outcomes import FailureReport

    report = FailureReport(
        code="PERSISTENCE_FAILURE",
        user_message="save failed",
        technical_detail="traceback",
    )
    assert report.code == "PERSISTENCE_FAILURE"
    payload = report.to_payload()
    assert payload["code"] == "PERSISTENCE_FAILURE"


def test_payload_shape_matches_frontend_contract():
    report = describe_failure(
        _make_result(SolverStatus.INFEASIBLE, "x"),
    )
    payload = report.to_payload()
    assert set(payload) == {"code", "message", "hints"}
    assert isinstance(payload["hints"], list)
