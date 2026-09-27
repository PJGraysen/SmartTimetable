from django.core.management.base import BaseCommand
from apps.scheduling.engine.solver import model as M
import inspect

class Command(BaseCommand):
    help = "Dump the full body of _add_grade10_option_block_constraints"
    def handle(self, *a, **kw):
        fn = M.SolverModelBuilder._add_grade10_option_block_constraints
        print(inspect.getsource(fn))
