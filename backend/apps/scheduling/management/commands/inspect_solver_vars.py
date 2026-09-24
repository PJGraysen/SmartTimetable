from django.core.management.base import BaseCommand
import inspect

class Command(BaseCommand):
    def handle(self, *a, **kw):
        from apps.scheduling.engine.solver.variables import AssignmentVariable
        from apps.scheduling.engine.solver.model import SolverModel

        print("=== AssignmentVariable source ===")
        print(inspect.getsource(AssignmentVariable))
        print()
        print("=== SolverModel.__init__ source ===")
        try:
            print(inspect.getsource(SolverModel.__init__))
        except Exception as e:
            print("no __init__:", e)
        print()
        print("=== SolverModel public methods ===")
        for name, m in inspect.getmembers(SolverModel, predicate=inspect.isfunction):
            if not name.startswith("_"):
                try:
                    sig = inspect.signature(m)
                    print(f"  {name}{sig}")
                except Exception:
                    print(f"  {name}")
        print()
        print("=== SolverModel instance attrs (from build) ===")
        try:
            attrs = [a for a in dir(SolverModel) if not a.startswith("__")]
            for a in attrs:
                print("  ", a)
        except Exception as e:
            print("  err:", e)
