from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Audit all teachers against the authoritative assignment doc"
    def handle(self, *a, **kw):
        Teacher = M("Teacher"); LR = M("LessonRequirement")
        TFA = M("TeacherFreeAfternoon")

        print(f"{'CODE':6s} {'NAME':22s} {'REQ':>4s} {'FA':>3s} {'CAP':>4s} {'DELTA':>6s}  ASSIGNMENTS")
        print("-" * 130)
        for t in Teacher.objects.filter(is_active=True).order_by("employee_code"):
            reqs = LR.objects.filter(teacher=t, is_active=True).select_related("instructional_group","subject")
            total = sum(r.lessons_per_week for r in reqs)
            if total == 0: continue
            fa = TFA.objects.filter(teacher=t, is_active=True).count()
            cap = 50 - (fa * 3)
            delta = cap - total
            flag = "  **OVER**" if delta < 0 else ""
            subs = defaultdict(list)
            for r in reqs:
                ig = r.instructional_group.name if r.instructional_group else "?"
                sc = r.subject.code if r.subject else "?"
                subs[sc].append(ig)
            summary = "; ".join(f"{sc}:{','.join(sorted(set(igs)))}" for sc, igs in sorted(subs.items()))
            print(f"{getattr(t,'employee_code',None)!s:6s} {str(t)[:22]:22s} {total:4d} {fa:3d} {cap:4d} {delta:+6d}{flag}  {summary[:80]}")
