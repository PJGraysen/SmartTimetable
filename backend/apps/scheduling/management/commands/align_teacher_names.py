from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Align DB teacher display names with master sheet authoritative names"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        Teacher = M("Teacher")

        # code -> (master_sheet_name, first, last)
        # master sheet uses these display names; keep employee_code as key
        ALIGNMENT = {
            "T003": ("Fr. Peter",      "Fr.",  "Peter"),     # was Fr. Mburu
            "T007": ("Ms. Mwangi",     "Ms.",  "Mwangi"),    # was Madam Prisca
            "T015": ("Ms. Karanja",    "Ms.",  "Karanja"),   # was Madam Maryann
            "T019": ("Mr. Gachagui",   "Mr.",  "Gachagui"),  # was Mr. Peter
        }

        print(f"{'CODE':6s}  {'CURRENT':32s}  ->  {'MASTER':28s}")
        print("-" * 76)
        actions = []
        for code, (display, first, last) in ALIGNMENT.items():
            t = Teacher.objects.filter(employee_code=code).first()
            if not t:
                print(f"{code:6s}  NOT FOUND"); continue
            cur = f"{t.first_name} {t.last_name}".strip() or "?"
            if cur == display:
                print(f"{code:6s}  {cur:32s}  already correct")
                continue
            print(f"{code:6s}  {cur:32s}  ->  {display:28s}")
            actions.append((t, first, last))

        if not kw["apply"]:
            print()
            print(f">> DRY RUN. {len(actions)} change(s). Add --apply to persist.")
            return

        with transaction.atomic():
            for t, first, last in actions:
                t.first_name = first
                t.last_name = last
                t.save(update_fields=["first_name", "last_name"])
        print()
        print(f"Applied {len(actions)} rename(s).")

        # Verify final state
        print()
        print("=== Final teacher list (code, name) ===")
        for t in Teacher.objects.filter(is_active=True).order_by("employee_code"):
            print(f"  {getattr(t,'employee_code',None):8s}  {str(t)}")
