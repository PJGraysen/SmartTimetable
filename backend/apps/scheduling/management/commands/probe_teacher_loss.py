from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Compare block LessonRequirements to persisted block entries for Grade 11"
    def handle(self, *a, **kw):
        IG = M("InstructionalGroup"); LR = M("LessonRequirement")
        TV = M("TimetableVersion")

        print("=== Grade 11 LessonRequirements (BLOCK only) ===")
        for gname in ("Grade 11E", "Grade 11W"):
            g = IG.objects.filter(name=gname).first()
            if not g: continue
            print(f"\n{gname}:")
            for lr in LR.objects.filter(instructional_group=g, requirement_type="BLOCK").select_related("subject", "teacher"):
                t = lr.teacher.employee_code if lr.teacher else "NONE"
                print(f"  {lr.subject.code:6s} lpw={lr.lessons_per_week} teacher={t} active={lr.is_active}")

        print("\n=== Grade 10 LessonRequirements (BLOCK only) — baseline ===")
        for gname in ("Grade 10E", "Grade 10W"):
            g = IG.objects.filter(name=gname).first()
            if not g: continue
            print(f"\n{gname}:")
            for lr in LR.objects.filter(instructional_group=g, requirement_type="BLOCK").select_related("subject", "teacher"):
                t = lr.teacher.employee_code if lr.teacher else "NONE"
                print(f"  {lr.subject.code:6s} lpw={lr.lessons_per_week} teacher={t} active={lr.is_active}")

        print("\n=== Persisted entries with NULL teacher, per group ===")
        latest = TV.objects.order_by("-version_number").first()
        from collections import Counter
        null_teacher = Counter()
        total = Counter()
        for e in latest.entries.select_related("instructional_group", "lesson_requirement"):
            gname = getattr(e.instructional_group, "name", "?")
            total[gname] += 1
            if e.teacher_id is None:
                null_teacher[gname] += 1
        for gname in sorted(total):
            print(f"  {gname:12s}  null_teacher={null_teacher[gname]:3d} / {total[gname]:3d}")
