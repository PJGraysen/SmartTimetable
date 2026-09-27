from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Compare TeacherAssignment rows for Grade 10 vs Grade 11"
    def handle(self, *a, **kw):
        IG = M("InstructionalGroup"); LR = M("LessonRequirement")
        TA = M("TeacherAssignment")

        # Inspect TA shape
        print("=== TeacherAssignment fields ===")
        for f in TA._meta.get_fields():
            if hasattr(f, "attname"):
                print(f"  {f.name:30s} {type(f).__name__}")

        print("\n=== Per-group TeacherAssignment counts ===")
        for gname in ("Grade 10E","Grade 10W","Grade 11E","Grade 11W",
                      "Grade 9E","Grade 9W","Form 4E","Form 4W"):
            g = IG.objects.filter(name=gname).first()
            if not g: continue
            lrs = LR.objects.filter(instructional_group=g, is_active=True)
            n_lr = lrs.count()
            n_ta = 0
            for lr in lrs:
                # TA likely has a FK to lesson_requirement
                try:
                    n_ta += TA.objects.filter(lesson_requirement=lr).count()
                except Exception:
                    pass
            print(f"  {gname:12s} requirements={n_lr:3d}  TeacherAssignments={n_ta:3d}")

        print("\n=== Sample TA rows for Grade 11E ===")
        g11 = IG.objects.filter(name="Grade 11E").first()
        if g11:
            lrs = LR.objects.filter(instructional_group=g11, is_active=True)[:5]
            for lr in lrs:
                tas = TA.objects.filter(lesson_requirement=lr)
                print(f"  LR={lr.subject.code:6s} teacher_fk={lr.teacher.employee_code if lr.teacher else 'None':6s}  TAs={tas.count()}")
