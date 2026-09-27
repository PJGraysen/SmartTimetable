from django.core.management.base import BaseCommand
from apps.scheduling.engine.solver import model as M
import inspect

class Command(BaseCommand):
    help = "Show full body of Grade 10 cross-class sync + block learner groups map"
    def handle(self, *a, **kw):
        fn = M.SolverModelBuilder._add_grade10_cross_class_synchronization_constraints
        print("=== _add_grade10_cross_class_synchronization_constraints ===")
        print(inspect.getsource(fn))
        print()
        print("=== GRADE10_BLOCK_LEARNER_GROUPS ===")
        print(f"  {getattr(M, 'GRADE10_BLOCK_LEARNER_GROUPS', None)}")
