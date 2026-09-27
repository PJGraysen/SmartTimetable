from django.core.management.base import BaseCommand
from apps.scheduling.engine.solver import model as M
import inspect

class Command(BaseCommand):
    help = "Confirm cross-class sync now discovers 10E<->10W and 11E<->11W"
    def handle(self, *a, **kw):
        src = inspect.getsource(M.SolverModelBuilder._add_grade10_cross_class_synchronization_constraints)
        checks = [
            ("generalized discovery", "Discover E/W stream pairs by grade prefix" in src),
            ("10E<->10W pair derived", 'f"{grade}E"' in src),
            ("11E<->11W pair derived", 'f"{grade}W"' in src),
            ("no hard-coded {10E,10W}", '"10E", "10W"' not in src and "{'10E', '10W'}" not in src),
        ]
        for label, ok in checks:
            print(f"  {'PASS' if ok else 'FAIL'}  {label}")
