from django.core.management.base import BaseCommand
from django.apps import apps
import inspect

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Probe senior-school recognition for Grade 11"
    def handle(self, *a, **kw):
        IG = M("InstructionalGroup")

        # Locate the two gate functions
        from apps.scheduling.engine.solver import model as M2
        from apps.scheduling.engine.solver import infeasibility_diagnostics as D2

        print("=== is_senior_school_instructional_group ===")
        for mod_name, mod in (("model", M2), ("diagnostics", D2)):
            for name in dir(mod):
                if "senior_school_instructional_group" in name or name == "is_senior_school_instructional_group":
                    fn = getattr(mod, name)
                    if callable(fn):
                        try:
                            print(f"\n--- {mod_name}.{name} ---")
                            print(inspect.getsource(fn))
                        except Exception as e:
                            print(f"  (could not get source: {e})")

        print()
        print("=== Live test against actual groups ===")
        fn = getattr(M2, "is_senior_school_instructional_group", None)
        if not fn:
            print("  NOT FOUND in model.py — checking diagnostics")
            fn = getattr(D2, "is_senior_school_instructional_group", None)
        if not fn:
            print("  NOT FOUND anywhere — solver may use a different gate name")
            return
        for g in IG.objects.all().order_by("name"):
            try:
                result = fn(g)
            except Exception as e:
                result = f"ERR: {e}"
            print(f"  {g.name:12s} -> {result}")

        print()
        print("=== SENIOR_SCHOOL_BLOCK_SLOTS keys ===")
        slots = getattr(M2, "SENIOR_SCHOOL_BLOCK_SLOTS", None)
        if slots:
            for k in sorted(slots):
                print(f"  {k}: {slots[k]}")
        else:
            print("  not found")
