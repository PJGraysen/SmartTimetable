from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    help = "Fix T017/T018 names and align subject assignments with authoritative mapping"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        Teacher = M("Teacher")
        LR = M("LessonRequirement")
        apply = kw["apply"]

        t17 = Teacher.objects.filter(employee_code="T017").first()
        t18 = Teacher.objects.filter(employee_code="T018").first()
        if not t17 or not t18:
            print("T017 or T018 not found"); return

        print(f"BEFORE:")
        print(f"  T017: first='{t17.first_name}' last='{t17.last_name}'")
        print(f"  T018: first='{t18.first_name}' last='{t18.last_name}'")
        print()

        # Rename per authoritative mapping
        # T017 = Mr. Baraza
        # T018 = Mr. Namuye
        print("RENAME:")
        print(f"  T017 -> Mr. Baraza")
        print(f"  T018 -> Mr. Namuye")
        print()

        if apply:
            with transaction.atomic():
                t17.first_name = "Mr."
                t17.last_name = "Baraza"
                t17.save(update_fields=["first_name", "last_name"])
                t18.first_name = "Mr."
                t18.last_name = "Namuye"
                t18.save(update_fields=["first_name", "last_name"])
            print("Renamed.")

        # Report current subject assignments (informational — do not change)
        print()
        print("=== Current assignments ===")
        for label, t in (("T017", t17), ("T018", t18)):
            print(f"\n{label} ({t}):")
            for r in LR.objects.filter(teacher=t, is_active=True).select_related(
                "instructional_group", "subject"
            ).order_by("instructional_group__name", "subject__code"):
                ig = r.instructional_group.name if r.instructional_group else "?"
                sub = r.subject.code if r.subject else "?"
                print(f"   {ig:14s} {sub:6s} n={r.lessons_per_week}")
