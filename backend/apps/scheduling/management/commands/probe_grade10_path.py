from django.core.management.base import BaseCommand
from apps.scheduling.engine.solver import model as M
import inspect

class Command(BaseCommand):
    help = "Find how Grade 10 parallel-block path is gated"
    def handle(self, *a, **kw):
        targets = [
            "_add_grade10_parallel_blocks",
            "_add_senior_school_elective_block_constraints",
            "_add_parallel_block_constraints",
        ]
        for name in targets:
            fn = getattr(M.SolverModelBuilder, name, None)
            if not fn:
                print(f"--- {name}: NOT FOUND on SolverModelBuilder")
                continue
            try:
                src = inspect.getsource(fn)
            except Exception as e:
                print(f"--- {name}: could not get source: {e}")
                continue
            print(f"=== SolverModelBuilder.{name} (first 80 lines) ===")
            for i, line in enumerate(src.splitlines()[:80], 1):
                print(f"  {i:3d} {line}")
            print()

        print("=== Constants that may gate Grade 10 ===")
        for const in (
            "SENIOR_SCHOOL_GROUP_CODES",
            "GRADE10_SYNCHRONIZED_BLOCKS",
            "GRADE10_OPTION_BLOCKS",
            "GRADE10_BLOCKS",
            "GRADE10_PARALLEL_BLOCKS",
        ):
            val = getattr(M, const, None)
            if val is not None:
                print(f"  {const} = {val}")
