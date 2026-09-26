from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m


class Command(BaseCommand):
    help = "Move Grade 9 CAS + SOCIAL off T014 to T018/T020"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        LR = M("LessonRequirement")
        TA = M("TeacherAssignment")
        Teacher = M("Teacher")
        IG = M("InstructionalGroup")

        t14 = Teacher.objects.filter(employee_code="T014").first()
        t18 = Teacher.objects.filter(employee_code="T018").first()
        t20 = Teacher.objects.filter(employee_code="T020").first()

        if not all([t14, t18, t20]):
            print("Missing T014/T018/T020"); return

        # Plan: Grade 9 CAS → T018, Grade 9 SOCIAL → T020
        PLAN = [
            ("Grade 9E", "CAS",    t18),
            ("Grade 9W", "CAS",    t18),
            ("Grade 9E", "SOCIAL", t20),
            ("Grade 9W", "SOCIAL", t20),
        ]

        print("=== PLAN ===")
        actions = []
        for gname, subj, t_to in PLAN:
            ig = IG.objects.filter(name=gname).first()
            if not ig:
                print(f"  {gname} not found"); continue
            r = LR.objects.filter(instructional_group=ig, subject__code=subj, is_active=True).first()
            if not r:
                print(f"  {gname} {subj} LR not found"); continue
            t_from = r.teacher
            if t_from and t_from.pk == t_to.pk:
                print(f"  SKIP {gname} {subj} — already {t_to}")
                continue
            print(f"  {gname} {subj} (n={r.lessons_per_week}): {t_from} -> {t_to}")
            actions.append((r, t_to))

        if not actions:
            print("\nNo actions needed."); return

        print()
        print("=== Projected loads ===")
        # Current totals
        def total_for(t):
            return sum(r.lessons_per_week for r in LR.objects.filter(teacher=t, is_active=True))
        cur = {t14: total_for(t14), t18: total_for(t18), t20: total_for(t20)}
        proj = dict(cur)
        for r, t_to in actions:
            if r.teacher:
                proj[r.teacher] = proj.get(r.teacher, 0) - r.lessons_per_week
            proj[t_to] = proj.get(t_to, 0) + r.lessons_per_week
        for t in [t14, t18, t20]:
            print(f"  {t}: {cur.get(t,0)} -> {proj.get(t,0)}")

        if not kw["apply"]:
            print()
            print(f">> DRY RUN — {len(actions)} change(s). Add --apply to persist.")
            return

        with transaction.atomic():
            for r, t_to in actions:
                r.teacher = t_to
                r.save(update_fields=["teacher"])
                ta = TA.objects.filter(lesson_requirement=r).first()
                if ta:
                    ta.teacher = t_to
                    ta.save(update_fields=["teacher"])
                else:
                    TA.objects.create(teacher=t_to, lesson_requirement=r, is_active=True)

        print(f"\nApplied {len(actions)} reassignment(s).")
        for t in [t14, t18, t20]:
            print(f"  {t}: now {sum(r.lessons_per_week for r in LR.objects.filter(teacher=t, is_active=True))}")
