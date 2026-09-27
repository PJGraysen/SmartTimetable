from django.core.management.base import BaseCommand
from apps.scheduling.engine.solver import model as M
import inspect

class Command(BaseCommand):
    help = "Show is_grade10_instructional_group source + live test"
    def handle(self, *a, **kw):
        # Find where it's imported from
        src = inspect.getsource(M)
        for line in src.splitlines():
            if "is_grade10_instructional_group" in line and "import" in line:
                print(f"IMPORT: {line.strip()}")
        print()

        fn = getattr(M, "is_grade10_instructional_group", None)
        if not fn:
            print("Function not directly importable from model module")
            return

        print("=== Source ===")
        try:
            print(inspect.getsource(fn))
        except Exception as e:
            print(f"  (no source: {e})")
        print()
        print(f"Defined in: {fn.__module__}")

        print()
        print("=== Live test ===")
        apps = __import__("django.apps", fromlist=["apps"])
        IG = None
        for m in apps.apps.get_models():
            if m.__name__ == "InstructionalGroup":
                IG = m; break
        for name in ("Grade 10E", "Grade 10W", "Grade 11E", "Grade 11W",
                     "Form 3E", "Form 4E", "Grade 8E", "Grade 9E"):
            g = IG.objects.filter(name=name).first()
            if not g:
                print(f"  {name:12s} (not found)"); continue
            try:
                print(f"  {name:12s} code={g.code:5s} -> {fn(g)}")
            except Exception as e:
                print(f"  {name:12s} -> ERR {e}")
