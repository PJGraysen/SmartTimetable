from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    def handle(self, *a, **kw):
        IG = M("InstructionalGroup"); LR = M("LessonRequirement")
        Teacher = M("Teacher")

        print("=== All InstructionalGroups ===")
        for ig in IG.objects.all().order_by("name"):
            n_lr = LR.objects.filter(instructional_group=ig, is_active=True).count()
            print(f"  {ig.name:15s} active={ig.is_active}  active_LRs={n_lr}  pk={str(ig.pk)[:8]}")

        print()
        print("=== Teacher load summary (active LRs) ===")
        by_teacher = defaultdict(int)
        for r in LR.objects.filter(is_active=True).select_related("teacher"):
            if r.teacher_id:
                by_teacher[r.teacher_id] += r.lessons_per_week
        for t in Teacher.objects.filter(is_active=True).order_by("employee_code"):
            load = by_teacher.get(t.pk, 0)
            if load > 0:
                print(f"  {getattr(t,'employee_code',None):8s} {str(t)[:28]:28s} {load:3d}")

        print()
        total_active = sum(by_teacher.values())
        print(f"TOTAL active lessons in DB: {total_active}")
