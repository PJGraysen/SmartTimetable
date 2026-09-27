from django.core.management.base import BaseCommand
from apps.scheduling.engine.solver import model as M
import inspect

class Command(BaseCommand):
    help = "Show subsumption logic to confirm grade guard is missing"
    def handle(self, *a, **kw):
        for name in (
            "_synchronized_teacher_event_groups",
            "_synchronized_teacher_event_subsumed_keys",
            "_add_teacher_clash_constraints",
        ):
            fn = getattr(M.SolverModelBuilder, name, None)
            if not fn:
                print(f"(missing) {name}"); continue
            print(f"\n===== {name} =====")
            print(inspect.getsource(fn))
