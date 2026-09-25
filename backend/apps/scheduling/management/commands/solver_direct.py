from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m


class Command(BaseCommand):
    help = "Direct solver run to expose the raw CP-SAT status"

    def handle(self, *a, **kw):
        from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
        from apps.scheduling.engine.solver.model import SolverModelBuilder
        from apps.scheduling.engine.solver.solver import CPSATSolver
        from apps.scheduling.engine.solver.objective import (
            BalancedTeacherWorkloadObjective,
            CompositeSolverObjective,
            TeacherConsecutivePeriodObjective,
        )
        from collections import Counter

        Term = M("Term")
        term = Term.objects.filter(is_active=True).first() or Term.objects.first()
        print(f"Term: {term}")

        print("=== Loading problem ===")
        problem = DjangoSchedulingLoader().load_problem(term=term)
        print(f"  periods:                {len(getattr(problem, 'periods', []) or [])}")
        print(f"  instructional_groups:   {len(getattr(problem, 'instructional_groups', []) or [])}")
        print(f"  teachers:               {len(getattr(problem, 'teachers', []) or [])}")
        print(f"  rooms:                  {len(getattr(problem, 'rooms', []) or [])}")
        print(f"  lesson_requirements:    {len(getattr(problem, 'lesson_requirements', []) or [])}")
        active_lrs = [r for r in (getattr(problem, 'lesson_requirements', []) or []) if getattr(r, 'is_active', True)]
        print(f"    active:               {len(active_lrs)}")

        by_group = Counter()
        for r in active_lrs:
            by_group[str(getattr(r, 'instructional_group_id', '?'))] += int(getattr(r, 'periods_per_week', 0) or 0)
        print(f"  per-group total load:")
        for g in (getattr(problem, 'instructional_groups', []) or []):
            gid = str(getattr(g, 'id', ''))
            name = getattr(g, 'code', None) or getattr(g, 'name', '?')
            print(f"    {str(name):24s} total={by_group.get(gid, 0)}")

        print()
        print("=== Building SolverModel ===")
        objective = CompositeSolverObjective(objectives=(
            BalancedTeacherWorkloadObjective(),
            TeacherConsecutivePeriodObjective(),
        ))
        builder = SolverModelBuilder(objective=objective)
        solver_model = builder.build(problem)
        print(f"  variables:              {len(solver_model.variables)}")

        print()
        print("=== Solving (60s timeout, no diversity constraint) ===")
        solver = CPSATSolver(time_limit_seconds=300.0, num_workers=1)
        result = solver.solve(problem=problem, solver_model=solver_model)

        print()
        print(f"STATUS:        {result.status}")
        stats = getattr(result, 'statistics', None)
        if stats is not None:
            for attr in ("num_conflicts", "num_branches", "wall_time", "num_booleans"):
                if hasattr(stats, attr):
                    print(f"STAT_{attr.upper()}:  {getattr(stats, attr)}")
        msg = getattr(result, 'error_message', None)
        if msg:
            print(f"ERROR_MSG:     {msg[:2000]}")
        print(f"Assignments:   {len(getattr(result, 'assignments', []) or [])}")
