from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Dump DB teacher → subject × class mapping (block-aware)"
    def handle(self, *a, **kw):
        Teacher = M("Teacher"); LR = M("LessonRequirement")
        print(f"{'CODE':8s} {'NAME':26s} {'SUBJECT':10s} {'CLASS':14s} {'N':>3s}")
        print("-" * 70)
        # active only, sorted by code
        for t in Teacher.objects.filter(is_active=True).order_by("employee_code"):
            reqs = LR.objects.filter(teacher=t, is_active=True).select_related(
                "subject", "instructional_group"
            ).order_by("subject__code", "instructional_group__name")
            if not reqs:
                continue
            for r in reqs:
                sub = r.subject.code if r.subject else "?"
                ig = r.instructional_group.name if r.instructional_group else "?"
                print(f"{t.employee_code or '':8s} {str(t)[:26]:26s} {sub:10s} {ig:14s} {r.lessons_per_week:3d}")
        print()
        print("Note: DB 'employee_code' is authoritative. Master sheet number is",
              "not always aligned to T-number (T007/T015/T019 pending confirmation).")
