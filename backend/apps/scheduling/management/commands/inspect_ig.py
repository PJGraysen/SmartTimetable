from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Inspect InstructionalGroup schema + existing groups"
    def handle(self, *a, **kw):
        IG = M("InstructionalGroup")
        print("=== Fields ===")
        for f in IG._meta.get_fields():
            if hasattr(f, "column"):
                null = "NULL" if getattr(f, "null", False) else "NOT NULL"
                blank = "blank" if getattr(f, "blank", False) else ""
                print(f"  {f.name:30s} {type(f).__name__:20s} {null} {blank}")
        print()
        print("=== Existing groups ===")
        for g in IG.objects.all().order_by("name"):
            print(f"  {str(g.pk)[:8]}  {g.name}")
