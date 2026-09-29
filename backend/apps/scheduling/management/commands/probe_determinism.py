from django.core.management.base import BaseCommand
from django.apps import apps
import dataclasses
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver
from apps.scheduling.engine.solver.objective import (
    BalancedTeacherWorkloadObjective,
    CompositeSolverObjective,
    TeacherConsecutivePeriodObjective,
)
from apps.scheduling.engine.domain.entities import SchedulingAssignment


def M(n):
    for m in apps.get_models():
        if m.__name__ == n:
            return m


def _asg_key(a):
    """Best-effort stable key. Works on dataclass or plain object."""
    parts = []
    for f in dataclasses.fields(a) if dataclasses.is_dataclass(a) else []:
        parts.append((f.name, repr(getattr(a, f.name, None))))
    if not parts:
        for name in ("instructional_group_id", "group_id", "subject_code", "subject_id",
                     "day", "period_id", "period_index", "teacher_id", "room_id"):
            parts.append((name, repr(getattr(a, name, None))))
    return tuple(parts)


class Command(BaseCommand):
    help = "Run the solver twice on the same problem; report determinism."

    def handle(self, *a, **kw):
        print("SchedulingAssignment fields:")
        for f in dataclasses.fields(SchedulingAssignment):
            print(f"  {f.name}: {f.type}")
        print()

        Term = M("Term")
        term = Term.objects.filter(is_active=True).first() or Term.objects.first()
        print(f"Term: {term}")

        print("Loading problem (once)...")
        problem = DjangoSchedulingLoader().load_problem(term=term)

        def build_and_solve(tag):
            objective = CompositeSolverObjective(objectives=(
                BalancedTeacherWorkloadObjective(),
                TeacherConsecutivePeriodObjective(),
            ))
            builder = SolverModelBuilder(objective=objective)
            model = builder.build(problem)
            solver = CPSATSolver(time_limit_seconds=300.0, num_workers=1)
            result = solver.solve(problem=problem, solver_model=model)
            asg = getattr(result, "assignments", None) or ()
            fp = sorted(_asg_key(a) for a in asg)
            print(f"  [{tag}] status={getattr(result, 'status', '?')}  assignments={len(asg)}")
            return fp, asg

        print("Solve #1...")
        fp1, asg1 = build_and_solve("run1")
        print("Solve #2...")
        fp2, asg2 = build_and_solve("run2")

        print()
        if not asg1 and not asg2:
            print("Both runs returned zero assignments - can't fingerprint.")
            return
        if fp1 == fp2:
            print("RESULT: DETERMINISTIC - both solves produced identical assignments.")
        else:
            only1 = set(fp1) - set(fp2)
            only2 = set(fp2) - set(fp1)
            print("RESULT: NON-DETERMINISTIC")
            print(f"  unique to run1: {len(only1)}")
            print(f"  unique to run2: {len(only2)}")
            print(f"  common:         {len(set(fp1) & set(fp2))}")
            print("  sample only-in-run1:")
            for x in list(only1)[:2]:
                print(f"    {x}")
            print("  sample only-in-run2:")
            for x in list(only2)[:2]:
                print(f"    {x}")
