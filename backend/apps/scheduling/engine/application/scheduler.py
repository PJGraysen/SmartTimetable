from __future__ import annotations

from dataclasses import dataclass

from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.objective import (
    TeacherGapMinimizationObjective,
    BalancedTeacherWorkloadObjective,
    ComplexSubjectAdjacencyObjective,
    CompositeSolverObjective,
    ScopedStayPutObjective,
    MathsMorningPreferenceObjective,
    TeacherMaxConsecutiveObjective,
    TeacherDailyLoadObjective,
    SolverObjective,
    TeacherConsecutivePeriodObjective,
)
from apps.scheduling.engine.solver.result import SolverResult
from apps.scheduling.engine.solver.solver import CPSATSolver


@dataclass(slots=True)
class SchedulingService:
    """
    Application-level orchestration service for timetable generation.
    """

    model_builder: SolverModelBuilder
    solver: CPSATSolver

    def generate(
        self,
        problem: SchedulingProblem,
    ) -> SolverResult:
        """
        Generate a timetable for the supplied scheduling problem.
        """

        # --- Block-slot rotation (SmartTimetable Pro) ---
        # Safe swap range restricted to P2/P3 - proven feasible slots.
        try:
            import os as _os_rot
            from apps.scheduling.models import TimetableVersion as _TVrot
            from apps.scheduling.engine.application.grade10_parallel_blocks import (
                set_block_rotation_offset as _set_rot,
            )
            _forced = _os_rot.environ.get("ST_BLOCK_ROTATION_OFFSET")
            if _forced is not None:
                _rot = int(_forced)
            else:
                _prev = _TVrot.objects.order_by("-version_number").first()
                _rot = ((_prev.version_number + 1) if _prev else 0)
            _set_rot(_rot)
            import sys as _s_rot
            print(f"[ROTATION] offset={_rot} (mod2={_rot % 2})", file=_s_rot.stderr)
        except Exception as _e_rot:
            import sys as _s2
            import traceback as _tb
            print(f"[ROTATION] FAILED: {_e_rot}", file=_s2.stderr)
            _tb.print_exc(file=_s2.stderr)
        # --- end block-slot rotation ---

        solver_model = self.model_builder.build(problem)

        # --- Diversity vs previous version (SmartTimetable Pro) ---
        # Per-class cap at 0.30: at most 30% of a class's weekly lessons
        # may repeat the previous version, forcing >=70% change per class.
        # (0.15 was too tight for Form 4's pinned block slots.)
        # Scoped regenerations must preserve the out-of-scope layout.
        # The diversity constraint enforces >=70% change per class,
        # which is directly incompatible with that; skip it whenever
        # hints are present. Master runs (no hints) keep the rule.
        _hints_present = bool(getattr(problem, "hint_assignments", ()) or ())
        if _hints_present:
            import sys as _s_skip
            print(
                "[DIVERSITY] skipped: scoped hints present",
                file=_s_skip.stderr,
            )
        else:
            try:
                import sys as _s2
                from collections import defaultdict as _dd2
                from apps.scheduling.models import (
                    TimetableVersion as _TVdiv,
                    TimetableEntry as _TEdiv,
                )
                _prev_div = _TVdiv.objects.order_by("-version_number").first()
                if _prev_div is not None:
                    _prev_map = {}
                    for _e in _TEdiv.objects.filter(
                        timetable_version=_prev_div
                    ).only(
                        "instructional_group_id",
                        "day",
                        "period_id",
                        "lesson_requirement_id",
                    ):
                        _prev_map[(
                            str(_e.instructional_group_id),
                            str(_e.day or "").upper(),
                            str(_e.period_id),
                        )] = str(_e.lesson_requirement_id)

                    if _prev_map:
                        _prev_per_class = _dd2(int)
                        for (_ig, _d, _p) in _prev_map:
                            _prev_per_class[_ig] += 1

                        _same_vars_per_class = _dd2(list)
                        for _v in solver_model.variables:
                            _k = (
                                str(_v.instructional_group_id),
                                str(_v.day or "").upper(),
                                str(_v.period_id),
                            )
                            if _prev_map.get(_k) == str(_v.lesson_requirement_id):
                                _same_vars_per_class[_k[0]].append(_v.variable)

                        _total_caps = 0
                        for _ig, _vs in _same_vars_per_class.items():
                            _n = _prev_per_class.get(_ig, 0)
                            if _n == 0:
                                continue
                            _limit = max(1, int(0.30 * _n))
                            solver_model.model.add(sum(_vs) <= _limit)
                            _total_caps += 1
                        print(
                            f"[DIVERSITY] per-class caps={_total_caps} limit=30pct",
                            file=_s2.stderr,
                        )
            except Exception as _de:
                import sys as _s3
                print(f"[DIVERSITY] skipped: {_de}", file=_s3.stderr)
        # --- end diversity ---

        return self.solver.solve(
            problem=problem,
            solver_model=solver_model,
        )


def create_default_scheduler(
    *,
    time_limit_seconds: float = 900.0,
    num_workers: int | None = None,
    objective: SolverObjective | None = None,
) -> SchedulingService:
    """
    Create the standard scheduling service configuration.

    The default scheduler combines the established workload/distribution
    objective with the teacher consecutive-period objective.
    """

    selected_objective = (
        objective
        if objective is not None
        else CompositeSolverObjective(
            objectives=(
                ScopedStayPutObjective(weight=1000),
                BalancedTeacherWorkloadObjective(),
                # Consecutive lessons: bump to 5 ? 4-in-a-row is heavily penalized
                TeacherConsecutivePeriodObjective(weight=5),
                # Teacher idle-gap penalty: keep moderate
                TeacherGapMinimizationObjective(weight=1),
                # --- New pedagogical soft rules ---
                # Science/science and science/maths adjacency is penalized,
                # practicals excluded. Maths is preferred in morning periods.
                ComplexSubjectAdjacencyObjective(),
                # MathsMorningPreferenceObjective(),  # disabled per business decision
                TeacherMaxConsecutiveObjective(weight=60),
                TeacherDailyLoadObjective(threshold=6, weight=8),
            ),
        )
    )

    return SchedulingService(
        model_builder=SolverModelBuilder(
            objective=selected_objective,
        ),
        solver=CPSATSolver(
            time_limit_seconds=time_limit_seconds,
            num_workers=num_workers,
        ),
    )
