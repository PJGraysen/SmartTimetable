from __future__ import annotations

from ortools.sat.python import cp_model
import pytest

from apps.scheduling.engine.solver.objective import (
    BalancedTeacherWorkloadObjective,
    CompositeSolverObjective,
    TeacherConsecutivePeriodObjective,
)


def test_composite_objective_rejects_objective_without_expression_builder():
    with pytest.raises(
        TypeError,
        match="requires objectives that implement build_expression",
    ):
        CompositeSolverObjective(
            objectives=(object(),),
        )


def test_composite_objective_accepts_empty_objectives():
    objective = CompositeSolverObjective(
        objectives=(),
    )

    assert objective.objectives == ()


def test_composite_objective_can_apply_to_model():
    model = cp_model.CpModel()

    variable = model.new_bool_var("penalty")

    class SimpleObjective:
        def build_expression(
            self,
            *,
            model,
            problem,
            variables,
        ):
            return variable

    objective = CompositeSolverObjective(
        objectives=(
            SimpleObjective(),
        ),
    )

    objective.apply(
        model=model,
        problem=None,
        variables=(),
    )

    solver = cp_model.CpSolver()

    status = solver.solve(model)

    assert status == cp_model.OPTIMAL
    assert solver.value(variable) == 0


def test_composite_objective_accepts_standard_objectives():
    objective = CompositeSolverObjective(
        objectives=(
            BalancedTeacherWorkloadObjective(),
            TeacherConsecutivePeriodObjective(),
        ),
    )

    assert len(objective.objectives) == 2
