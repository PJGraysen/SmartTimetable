from django.core.management.base import BaseCommand
from apps.scheduling.engine.solver import model as M
import inspect, pathlib

class Command(BaseCommand):
    help = "Print the two group gates and the entry points of Grade 10 constraints"
    def handle(self, *a, **kw):
        path = pathlib.Path(M.__file__)
        lines = path.read_text(encoding="utf-8").splitlines()

        def show(lo, hi, label):
            print(f"=== {label} (lines {lo}..{hi}) ===")
            for i in range(lo-1, min(hi, len(lines))):
                print(f"  {i+1:5d} {lines[i]}")
            print()

        show(1076, 1094, "_is_grade10_group / _is_senior_school_group / _grade10_block_code")
        show(1796, 1830, "_add_grade10_option_block_constraints (top 35)")
        show(2040, 2080, "_add_grade10_cross_class_synchronization_constraints (top 41)")

        print("=== build() lines that call Grade 10 methods ===")
        for i in range(632, 743):
            if "grade10" in lines[i].lower():
                print(f"  {i+1:5d} {lines[i]}")
