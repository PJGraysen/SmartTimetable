from django.core.management.base import BaseCommand
import pathlib, re

class Command(BaseCommand):
    help = "Find every place the pipeline writes/derives entry.teacher"
    def handle(self, *a, **kw):
        base = pathlib.Path("apps/scheduling/engine")
        # Files most likely to build/persist assignments
        targets = [
            base / "application" / "timetable_persistence.py",
            base / "solver" / "model.py",
            base / "infrastructure" / "django_loader.py",
            base / "domain" / "entities.py",
        ]
        kws = ("teacher", "Teacher")
        for path in targets:
            if not path.exists():
                print(f"(missing) {path}"); continue
            print(f"\n===== {path.relative_to(base)} =====")
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for kw in kws:
                    if kw in line:
                        print(f"  {lineno:5d}  {line.rstrip()}")
                        break
