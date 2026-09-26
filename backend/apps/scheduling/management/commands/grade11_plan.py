from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Show Grade 10 lesson-requirement pattern + teacher loads (before Grade 11 planning)"
    def handle(self, *a, **kw):
        LR = M("LessonRequirement"); IG = M("InstructionalGroup")
        Teacher = M("Teacher")

        # All Grade 10E lesson requirements — these will be the template for Grade 11
        for gname in ("Grade 10E", "Grade 10W"):
            ig = IG.objects.filter(name=gname).first()
            if not ig:
                print(f"{gname} not found"); continue
            print(f"=== {gname} (id={str(ig.pk)[:8]}) — the template ===")
            lrs = LR.objects.filter(instructional_group=ig, is_active=True).select_related("subject", "teacher")
            total = 0
            by_subj = {}
            for r in lrs:
                sc = r.subject.code if r.subject else "?"
                tn = r.teacher.employee_code if r.teacher else "?"
                tn_full = str(r.teacher) if r.teacher else "(none)"
                by_subj.setdefault(sc, []).append((r.lessons_per_week, tn_full))
                total += r.lessons_per_week
            for sc in sorted(by_subj):
                entries = by_subj[sc]
                n_total = sum(x[0] for x in entries)
                teachers = ", ".join(set(x[1] for x in entries))
                print(f"  {sc:8s}  {n_total:2d}/wk  [{teachers}]")
            print(f"  TOTAL: {total} lessons")
            print()

        # Teacher capacity BEFORE Grade 8 removal
        print("=== Current active teacher loads ===")
        active_lr = LR.objects.filter(is_active=True).select_related("teacher", "instructional_group")
        by_teacher = defaultdict(int)
        by_teacher_classes = defaultdict(set)
        for r in active_lr:
            if r.teacher_id:
                by_teacher[r.teacher_id] += r.lessons_per_week
                if r.instructional_group:
                    by_teacher_classes[r.teacher_id].add(r.instructional_group.name)
        for t in Teacher.objects.filter(is_active=True).order_by("employee_code"):
            load = by_teacher.get(t.pk, 0)
            classes = sorted(by_teacher_classes.get(t.pk, []))
            warn = "  <<< OVER" if load > 46 else ("  (near cap)" if load >= 42 else "")
            print(f"  {t.employee_code:6s}  {str(t)[:30]:30s}  load={load:3d}  classes={classes}{warn}")
