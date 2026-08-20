from apps.scheduling.engine.application.scheduler import (
    create_default_scheduler,
)
from apps.scheduling.engine.solver.objective import (
    CompositeSolverObjective,
)


def test_create_default_scheduler_uses_composite_default_objective():
    service = create_default_scheduler()

    assert isinstance(
        service.model_builder.objective,
        CompositeSolverObjective,
    )

    assert len(
        service.model_builder.objective.objectives
    ) == 2
