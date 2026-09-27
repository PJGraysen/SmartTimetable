from django.core.management.base import BaseCommand
import pathlib

class Command(BaseCommand):
    help = "Dump persistence code where entries are written"
    def handle(self, *a, **kw):
        path = pathlib.Path("apps/scheduling/engine/application/timetable_persistence.py")
        lines = path.read_text(encoding="utf-8").splitlines()
        print(f"Total lines: {len(lines)}\n")
        # Print lines 400-580 which contained the sibling/entry-writing logic
        for i in range(399, min(580, len(lines))):
            print(f"  {i+1:5d}  {lines[i]}")
