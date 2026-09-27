from django.core.management.base import BaseCommand
from importlib import import_module
import inspect

class Command(BaseCommand):
    help = "Read generate_grade10_parallel source to see scope + persistence"
    def handle(self, *a, **kw):
        mod = import_module("apps.scheduling.management.commands.generate_grade10_parallel")
        src = inspect.getsource(mod.Command)
        lines = src.splitlines()
        print(f"Total lines: {len(lines)}\n")

        keywords = (
            "instructional_group", "active", "GROUP", "grade10",
            "Grade 10", "Grade 11", "10E", "10W", "11E", "11W",
            "Timetable", "timetable", "create(", "update_or_create",
            "deactivate", "is_active", "persist", "publish",
            "solver", "Solver", "solve(",
        )
        for i, line in enumerate(lines, 1):
            for kw in keywords:
                if kw in line:
                    print(f"  {i:4d}  {line}")
                    break
