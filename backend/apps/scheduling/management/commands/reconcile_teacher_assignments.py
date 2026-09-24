from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
from collections import defaultdict

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    help = "Reconcile TeacherAssignment vs LessonRequirement.teacher"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
        p.add_argument("--teacher", default=None,
                       help="Optional employee_code to focus on (e.g. T011)")
    def handle(self, *a, **kw):
        Teacher = M("Teacher")
        LR = M("LessonRequirement")
        TA = M("TeacherAssignment")

        focus = kw["teacher"]

        # --- 1. Show T011 in both tables ---
        if focus:
            t = Teacher.objects.filter(employee_code=focus).first()
            if not t:
                print(f"{focus} not found"); return

            print(f"=== {focus} — LessonRequirement.teacher ===")
            lr_total = 0
            for r in LR.objects.filter(teacher=t, is_active=True).select_related(
                "instructional_group","subject"):
                ig = r.instructional_group.name if r.instructional_group else "?"
                sc = r.subject.code if r.subject else "?"
                print(f"  LR id={str(r.pk)[:8]} {ig:14s} {sc:6s} n={r.lessons_per_week}")
                lr_total += r.lessons_per_week
            print(f"  LR TOTAL: {lr_total}")
            print()

            print(f"=== {focus} — TeacherAssignment ===")
            ta_total = 0
            ta_rows = list(TA.objects.filter(teacher=t, is_active=True).select_related(
                "lesson_requirement__instructional_group",
                "lesson_requirement__subject"))
            for ta in ta_rows:
                r = ta.lesson_requirement
                ig = r.instructional_group.name if r and r.instructional_group else "?"
                sc = r.subject.code if r and r.subject else "?"
                n = r.lessons_per_week if r else 0
                lr_teacher = r.teacher if r else None
                print(f"  TA id={str(ta.pk)[:8]} LR id={str(r.pk)[:8] if r else '?'} "
                      f"{ig:14s} {sc:6s} n={n} LR.teacher={lr_teacher}")
                ta_total += n
            print(f"  TA TOTAL: {ta_total}")
            print()
            print(f"DIFF: LR={lr_total}  TA={ta_total}  (must match)")

        # --- 2. Find ALL rows where TA.teacher != LR.teacher ---
        print()
        print("=== Global mismatch: TeacherAssignment.teacher != LessonRequirement.teacher ===")
        mismatched = []
        for ta in TA.objects.filter(is_active=True).select_related(
            "teacher","lesson_requirement__instructional_group",
            "lesson_requirement__subject","lesson_requirement__teacher"):
            r = ta.lesson_requirement
            if r is None or not r.is_active:
                continue
            lr_t = r.teacher
            if lr_t is None:
                continue
            if ta.teacher_id != lr_t.pk:
                mismatched.append((ta, r, lr_t))

        print(f"  Found {len(mismatched)} mismatched TeacherAssignment row(s)")
        for ta, r, lr_t in mismatched[:40]:
            ig = r.instructional_group.name if r.instructional_group else "?"
            sc = r.subject.code if r.subject else "?"
            print(f"    TA id={str(ta.pk)[:8]} "
                  f"{ig:14s} {sc:6s} n={r.lessons_per_week:2d}  "
                  f"TA.teacher={ta.teacher}  LR.teacher={lr_t}")

        if not kw["apply"]:
            print()
            print(">> DRY RUN. Re-run with --apply to fix.")
            return

        # --- 3. Apply fix: point TA.teacher at LR.teacher ---
        with transaction.atomic():
            n = 0
            for ta, r, lr_t in mismatched:
                ta.teacher = lr_t
                ta.save(update_fields=["teacher"])
                n += 1
            print(f"\nUpdated {n} TeacherAssignment row(s)")

        # --- 4. Verify T011 load again ---
        if focus:
            t = Teacher.objects.filter(employee_code=focus).first()
            lr_total = sum(r.lessons_per_week for r in LR.objects.filter(teacher=t, is_active=True))
            ta_total = sum(
                ta.lesson_requirement.lessons_per_week
                for ta in TA.objects.filter(teacher=t, is_active=True).select_related("lesson_requirement")
                if ta.lesson_requirement
            )
            print(f"\n{focus} after fix: LR={lr_total}  TA={ta_total}")

