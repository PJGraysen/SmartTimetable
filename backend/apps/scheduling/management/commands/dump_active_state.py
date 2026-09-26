from django.core.management.base import BaseCommand
from django.apps import apps
from collections import Counter

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    def handle(self, *a, **kw):
        IG = M("InstructionalGroup")
        LR = M("LessonRequirement")
        TA = M("TeacherAssignment")

        print("=== Active LRs per class (what the solver sees) ===")
        for ig in IG.objects.filter(is_active=True).order_by("name"):
            reqs = LR.objects.filter(instructional_group=ig, is_active=True).select_related("subject")
            total = sum(r.lessons_per_week for r in reqs)
            subs = Counter()
            for r in reqs:
                subs[r.subject.code if r.subject else "?"] += r.lessons_per_week
            print(f"  {ig.name:14s} total={total:3d}  subjects={len(subs)}  {dict(subs)}")

        print()
        print("=== Teacher capacity check (active TeacherAssignment) ===")
        for t in M("Teacher").objects.filter(is_active=True).order_by("employee_code"):
            tas = TA.objects.filter(teacher=t, is_active=True).select_related("lesson_requirement")
            total = sum((ta.lesson_requirement.lessons_per_week if ta.lesson_requirement else 0) for ta in tas)
            if total > 40:
                print(f"  !! {t.employee_code:6s} {str(t)[:26]:26s} total={total}")
