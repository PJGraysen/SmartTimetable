from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    help = "Apply ENG reassignment and deactivate duplicate teacher records"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        Teacher = M("Teacher"); LR = M("LessonRequirement")
        apply = kw["apply"]

        # ---------- PART 1: ENG reassignment T011 -> T015 ----------
        t11 = Teacher.objects.filter(employee_code="T011").first()
        t15 = Teacher.objects.filter(employee_code="T015").first()
        if not t11 or not t15:
            print("!! T011 or T015 missing, abort"); return

        moves = LR.objects.filter(
            teacher=t11, is_active=True,
            instructional_group__name__in=["Form 4E","Form 4W"],
            subject__code="ENG",
        )
        print("=== PART 1: ENG F4E/F4W: T011 -> T015 ===")
        for r in moves:
            print(f"  {r.instructional_group.name} {r.subject.code} n={r.lessons_per_week}")
        print(f"  to move: {moves.count()}")

        # ---------- PART 2: detect duplicate teachers ----------
        DUPES = [
            "ALEX_BARASA","FELISTAS_MUMBI","GRACE_WANJIRU","JOHN_KAMAU",
            "LEWIS_NYAGAH","NDETTA_ACHIENG","PRISCA_MWANGI","SAMUEL_OTIENO",
        ]
        print()
        print("=== PART 2: duplicate teacher records ===")
        to_deactivate = []
        for code in DUPES:
            t = Teacher.objects.filter(employee_code=code).first()
            if not t:
                print(f"  {code:18s} not found — skip")
                continue
            reqs = LR.objects.filter(teacher=t, is_active=True).select_related("instructional_group","subject")
            n = reqs.count()
            total = sum(r.lessons_per_week for r in reqs)
            if n == 0:
                print(f"  {code:18s} pk={t.pk} {str(t)[:34]:34s} REQS=0  -> safe to deactivate")
                to_deactivate.append(t)
            else:
                print(f"  {code:18s} pk={t.pk} {str(t)[:34]:34s} REQS={n} total={total}  **HAS ACTIVE LOADS — do NOT deactivate**")
                for r in reqs:
                    ig = r.instructional_group.name if r.instructional_group else "?"
                    sc = r.subject.code if r.subject else "?"
                    print(f"        {ig:14s} {sc:8s} n={r.lessons_per_week}")

        # ---------- APPLY ----------
        if not apply:
            print()
            print(f">> DRY RUN. Would move {moves.count()} ENG requirement(s) and deactivate {len(to_deactivate)} dupe(s).")
            print(">> Re-run with --apply to persist.")
            return

        with transaction.atomic():
            n = 0
            for r in moves:
                r.teacher = t15
                r.save(update_fields=["teacher"])
                n += 1
            print(f"\nMoved {n} ENG requirement(s) T011 -> T015")

            d = 0
            for t in to_deactivate:
                t.is_active = False
                t.save(update_fields=["is_active"])
                d += 1
            print(f"Deactivated {d} duplicate teacher record(s)")

        # ---------- VERIFY ----------
        print()
        print("=== Post-apply loads ===")
        for code in ("T011","T015"):
            t = Teacher.objects.filter(employee_code=code).first()
            if t:
                total = sum(r.lessons_per_week for r in LR.objects.filter(teacher=t, is_active=True))
                print(f"  {code} {str(t)[:30]:30s} {total} lessons/week")

