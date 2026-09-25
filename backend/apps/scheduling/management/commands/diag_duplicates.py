from django.core.management.base import BaseCommand
from django.apps import apps
from collections import Counter

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    def handle(self, *a, **kw):
        LR = M("LessonRequirement")
        TA = M("TeacherAssignment")
        Teacher = M("Teacher")

        print("=== 1. Duplicate (teacher, LR) in TeacherAssignment ===")
        seen = Counter()
        for ta in TA.objects.filter(is_active=True):
            seen[(ta.teacher_id, ta.lesson_requirement_id)] += 1
        dupes = {k: v for k, v in seen.items() if v > 1}
        print(f"  count: {len(dupes)}")
        for k, v in list(dupes.items())[:20]:
            t = Teacher.objects.filter(pk=k[0]).first()
            r = LR.objects.filter(pk=k[1]).first()
            ig = r.instructional_group.name if r and r.instructional_group else "?"
            sc = r.subject.code if r and r.subject else "?"
            print(f"    teacher={t} LR={ig} {sc} count={v}")

        print()
        print("=== 2. Duplicate (group, subject, term) active LRs ===")
        lr_seen = Counter()
        for r in LR.objects.filter(is_active=True):
            lr_seen[(r.instructional_group_id, r.subject_id, r.term_id)] += 1
        lr_dupes = {k: v for k, v in lr_seen.items() if v > 1}
        print(f"  count: {len(lr_dupes)}")
        for k, v in list(lr_dupes.items())[:20]:
            rs = LR.objects.filter(instructional_group_id=k[0], subject_id=k[1], term_id=k[2], is_active=True)
            for r in rs:
                print(f"    {r.instructional_group.name} {r.subject.code} n={r.lessons_per_week} teacher={r.teacher} pk={str(r.pk)[:8]}")

        print()
        print("=== 3. Active LRs with no teacher ===")
        n = LR.objects.filter(is_active=True, teacher__isnull=True).count()
        print(f"  count: {n}")
        for r in LR.objects.filter(is_active=True, teacher__isnull=True)[:15]:
            print(f"    {r.instructional_group.name} {r.subject.code} n={r.lessons_per_week}")

        print()
        print("=== 4. Active LRs whose teacher is inactive ===")
        n = LR.objects.filter(is_active=True, teacher__is_active=False).count()
        print(f"  count: {n}")

        print()
        print("=== 5. Active TAs whose teacher or LR is inactive/missing ===")
        n = TA.objects.filter(is_active=True, teacher__is_active=False).count()
        print(f"  TA with inactive teacher: {n}")
        n = TA.objects.filter(is_active=True, lesson_requirement__is_active=False).count()
        print(f"  TA with inactive LR: {n}")

        print()
        print("=== 6. Duplicate employee_code on Teacher ===")
        codes = Counter(t.employee_code for t in Teacher.objects.filter(is_active=True) if t.employee_code)
        dcodes = {k: v for k, v in codes.items() if v > 1}
        print(f"  count: {len(dcodes)}")
        for k, v in dcodes.items():
            print(f"    {k} x {v}")

        print()
        print("=== 7. Active TAs vs active LRs: count comparison ===")
        print(f"  Active LessonRequirements: {LR.objects.filter(is_active=True).count()}")
        print(f"  Active TeacherAssignments: {TA.objects.filter(is_active=True).count()}")

        print()
        print("=== 8. TAs whose LR has a DIFFERENT teacher than the TA ===")
        n = 0
        for ta in TA.objects.filter(is_active=True).select_related("lesson_requirement"):
            r = ta.lesson_requirement
            if r and r.teacher_id and r.teacher_id != ta.teacher_id:
                n += 1
                if n <= 15:
                    print(f"    {r.instructional_group.name} {r.subject.code} TA.teacher={ta.teacher} LR.teacher={r.teacher}")
        print(f"  total mismatches: {n}")
