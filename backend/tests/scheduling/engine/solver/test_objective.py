from ortools.sat.python import cp_model
import pytest

from apps.scheduling.engine.solver.objective import (
    BalancedTeacherWorkloadObjective,
    ObjectiveTerm,
    SchedulingObjective,
)


def test_empty_objective_has_no_terms():
    objective = SchedulingObjective()

    assert objective.is_empty
    assert objective.terms == []
    assert objective.names() == ()
    assert objective.expression() == 0


def test_objective_rejects_empty_term_name():
    model = cp_model.CpModel()
    variable = model.new_bool_var("x")

    with pytest.raises(
        ValueError,
        match="Objective term name cannot be empty",
    ):
        ObjectiveTerm(
            name="",
            expression=variable,
        )


def test_objective_rejects_invalid_weight():
    model = cp_model.CpModel()
    variable = model.new_bool_var("x")

    with pytest.raises(
        ValueError,
        match="Objective term weight must be greater than zero",
    ):
        ObjectiveTerm(
            name="test",
            expression=variable,
            weight=0,
        )


def test_objective_registers_weighted_penalties():
    model = cp_model.CpModel()

    first = model.new_bool_var("first")
    second = model.new_bool_var("second")

    objective = SchedulingObjective()

    objective.add_penalty(
        name="first_penalty",
        expression=first,
        weight=10,
    )

    objective.add_penalty(
        name="second_penalty",
        expression=second,
        weight=5,
    )

    assert objective.names() == (
        "first_penalty",
        "second_penalty",
    )

    assert len(objective.terms) == 2
    assert not objective.is_empty


def test_objective_can_be_applied_to_cp_sat_model():
    model = cp_model.CpModel()

    variable = model.new_bool_var("penalty")

    objective = SchedulingObjective()

    objective.add_penalty(
        name="test_penalty",
        expression=variable,
        weight=10,
    )

    objective.apply(model)

    solver = cp_model.CpSolver()

    status = solver.solve(model)

    assert status == cp_model.OPTIMAL
    assert solver.value(variable) == 0


def test_objective_extend_adds_terms():
    model = cp_model.CpModel()

    first = model.new_bool_var("first")
    second = model.new_bool_var("second")

    objective = SchedulingObjective()

    objective.extend(
        (
            ObjectiveTerm(
                name="first",
                expression=first,
                weight=2,
            ),
            ObjectiveTerm(
                name="second",
                expression=second,
                weight=3,
            ),
        )
    )

    assert objective.names() == (
        "first",
        "second",
    )


def test_teacher_workload_objective_accepts_valid_weight():
    objective = BalancedTeacherWorkloadObjective(
        weight=5,
    )

    assert objective.weight == 5


def test_teacher_workload_objective_rejects_invalid_weight():
    with pytest.raises(
        ValueError,
        match="Teacher workload objective weight must be greater than zero",
    ):
        BalancedTeacherWorkloadObjective(
            weight=0,
        )
