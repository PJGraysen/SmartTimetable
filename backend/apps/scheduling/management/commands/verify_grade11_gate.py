from django.core.management.base import BaseCommand
from django.apps import apps
from apps.scheduling.engine.application.grade10_parallel_blocks import (
    is_grade10_instructional_group,
    GRADE10_PARALLEL_SUBJECT_TO_BLOCK,
)

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Verify Grade 11 now passes the option-block gate"
    def handle(self, *a, **kw):
        IG = M("InstructionalGroup")
        print("=== Gate check ===")
        for name in ("Grade 10E", "Grade 10W", "Grade 11E", "Grade 11W",
                     "Form 3E", "Form 4E", "Grade 8E", "Grade 9E"):
            g = IG.objects.filter(name=name).first()
            if not g:
                print(f"  {name:12s} (not found)"); continue
            print(f"  {name:12s} -> {is_grade10_instructional_group(g)}")
        print()
        print("=== Subject->block map (shared Gr10/Gr11) ===")
        for s, b in sorted(GRADE10_PARALLEL_SUBJECT_TO_BLOCK.items()):
            print(f"  {s:6s} -> {b}")
