from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Inventory of current library module"
    def handle(self, *a, **kw):
        for model_name in ("Book", "BookCopy", "Member", "Loan", "Reservation",
                           "Author", "Publisher", "Category", "Shelf",
                           "Fine", "LoanRule", "LibrarySettings"):
            m = M(model_name)
            if not m:
                print(f"  {model_name:18s} MISSING")
                continue
            print(f"  {model_name:18s} {m._meta.db_table}  rows={m.objects.count()}")
            for f in m._meta.get_fields():
                if hasattr(f, "column"):
                    print(f"      {f.name:28s} {type(f).__name__}")
