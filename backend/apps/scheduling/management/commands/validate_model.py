from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m


class Command(BaseCommand):
    help = "Build the model and run CP-SAT validate() to surface the MODEL_INVALID cause"

    def handle(self, *a, **kw):
        from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
        from apps.scheduling.engine.solver.model import SolverModelBuilder
        from apps.scheduling.engine.solver.objective import (
            BalancedTeacherWorkloadObjective,
            CompositeSolverObjective,
            TeacherConsecutivePeriodObjective,
        )
        from ortools.sat.python import cp_model

        Term = M("Term")
        term = Term.objects.filter(is_active=True).first() or Term.objects.first()
        problem = DjangoSchedulingLoader().load_problem(term=term)

        objective = CompositeSolverObjective(objectives=(
            BalancedTeacherWorkloadObjective(),
            TeacherConsecutivePeriodObjective(),
        ))
        builder = SolverModelBuilder(objective=objective)
        solver_model = builder.build(problem)

        model = solver_model.model
        print("=== validate() raw ===")
        try:
            errs = model.validate()
            if not errs:
                print("  validate() returned EMPTY — model structurally fine")
            else:
                print(f"  validate() returned {len(errs)} error(s):")
                for e in errs[:30]:
                    print(f"    - {e}")
        except Exception as e:
            print(f"  validate() raised: {type(e).__name__}: {e}")

        print()
        print("=== Solve and check status ===")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 20
        solver.parameters.num_search_workers = 1
        try:
            status = solver.solve(model)
            print(f"  CP-SAT status: {status}")
            try:
                print(f"  status name: {solver.status_name(status)}")
            except Exception:
                pass
        except Exception as e:
            print(f"  solve() raised: {type(e).__name__}: {e}")

        # Print proto size — sometimes helpful for scale
        try:
            proto = model.proto
            print()
            print(f"=== Model proto size ===")
            print(f"  constraints: {len(proto.constraints)}")
            print(f"  variables:   {len(proto.variables)}")
            # Check for obviously bad constraint shapes
            bad = 0
            for c in proto.constraints[:5000]:
                # Bool OR / AT MOST ONE with duplicate literals
                if c.WhichOneof("constraint") in ("bool_or", "at_most_one"):
                    lits = list(getattr(c, c.WhichOneof("constraint")).literals)
                    if len(lits) != len(set(lits)):
                        bad += 1
                        if bad <= 5:
                            print(f"  DUPLICATE LITERAL in {c.WhichOneof('constraint')}: {lits}")
            print(f"  total duplicate-literal constraints scanned: {bad}")
        except Exception as e:
            print(f"  proto inspection failed: {e}")
