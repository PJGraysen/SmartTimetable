from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m


class Command(BaseCommand):
    help = "Rebalance Grade 9 KIS/SOCIAL off Ms. Erambi (T014)"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        LR = M("LessonRequirement")
        TA = M("TeacherAssignment")
        Teacher = M("Teacher")
        IG = M("InstructionalGroup")

        # --- 1. Show T014 current load ---
        t14 = Teacher.objects.filter(employee_code="T014").first()
        print(f"=== T014 {t14} current load ===")
        total = 0
        for r in LR.objects.filter(teacher=t14, is_active=True).select_related(
            "instructional_group", "subject"
        ).order_by("instructional_group__name", "subject__code"):
            ig = r.instructional_group.name if r.instructional_group else "?"
            sc = r.subject.code if r.subject else "?"
            print(f"  {ig:14s} {sc:8s} n={r.lessons_per_week}")
            total += r.lessons_per_week
        print(f"  TOTAL: {total}")

        # --- 2. Show candidate teachers and their current load ---
        print()
        print("=== Candidate teachers ===")
        for code in ("T016", "T018", "T020"):
            t = Teacher.objects.filter(employee_code=code).first()
            if not t: continue
            tot = sum(r.lessons_per_week for r in LR.objects.filter(teacher=t, is_active=True))
            print(f"  {code} {str(t)[:30]:30s} total={tot}")

        # --- 3. Plan ---
        print()
        print("=== PLAN ===")
        # Grade 9 KIS  -> T018 (Mr. Namuye — Kiswahili specialist)
        # Grade 9 SOCIAL -> T020 (Ms. Wainaina — Kiswahili/Social room)
        assignments = {
            "T018": [("Grade 9E", "KIS"), ("Grade 9W", "KIS")],
            "T020": [("Grade 9E", "SOCIAL"), ("Grade 9W", "SOCIAL")],
        }
        plan_actions = []
        for code, pairs in assignments.items():
            t = Teacher.objects.filter(employee_code=code).first()
            if not t:
                print(f"  MISSING teacher {code}")
                continue
            for gname, subj in pairs:
                ig = IG.objects.filter(name=gname).first()
                if not ig: continue
                r = LR.objects.filter(instructional_group=ig, subject__code=subj, is_active=True).first()
                if not r: continue
                if r.teacher_id == t.pk:
                    print(f"  SKIP {gname} {subj} (already T{code[1:]})")
                    continue
                print(f"  {gname} {subj} -> {t}")
                plan_actions.append((r, t))

        if not kw["apply"]:
            print()
            print(f">> DRY RUN — {len(plan_actions)} LR change(s). Add --apply to persist.")
            return

        with transaction.atomic():
            for r, t in plan_actions:
                # update LR.teacher
                r.teacher = t
                r.save(update_fields=["teacher"])
                # update matching TA (or create if missing)
                ta = TA.objects.filter(lesson_requirement=r).first()
                if ta:
                    ta.teacher = t
                    ta.save(update_fields=["teacher"])
                else:
                    TA.objects.create(teacher=t, lesson_requirement=r, is_active=True)

        print()
        print(f"Applied {len(plan_actions)} reassignment(s).")

        # Verify T014 new load
        t14.refresh_from_db()
        total = sum(r.lessons_per_week for r in LR.objects.filter(teacher=t14, is_active=True))
        print(f"T014 new total: {total}")
