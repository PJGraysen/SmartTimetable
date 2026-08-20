from __future__ import annotations

from ortools.sat.python import cp_model

from apps.scheduling.engine.solver.objective import (
    NoOpSolverObjective,
    SolverObjective,
)


def test_no_op_solver_objective_does_not_modify_model():
    model = cp_model.CpModel()

    variable = model.new_bool_var("test_variable")

    NoOpSolverObjective().apply(
        model=model,
        problem=None,  # type: ignore[arg-type]
        variables=[],
    )

    model.add(variable == 1)

    solver = cp_model.CpSolver()

    status = solver.solve(model)

    assert status == cp_model.OPTIMAL
    assert solver.value(variable) == 1


def test_solver_objective_protocol_is_runtime_compatible():
    class TestObjective:
        def apply(
            self,
            *,
            model,
            problem,
            variables,
        ):
            model.minimize(sum(variable.variable for variable in variables))

    objective: SolverObjective = TestObjective()

    model = cp_model.CpModel()
    variable = model.new_bool_var("test_variable")

    objective.apply(
        model=model,
        problem=None,
        variables=[],
    )

    model.add(variable == 1)

    solver = cp_model.CpSolver()

    status = solver.solve(model)

    assert status == cp_model.OPTIMAL
    assert solver.value(variable) == 1
