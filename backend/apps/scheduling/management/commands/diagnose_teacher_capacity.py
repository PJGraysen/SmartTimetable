from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    help = "Diagnose over-committed teachers"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
        p.add_argument("--code", default="T011")
    def handle(self, *a, **kw):
        Teacher = M("Teacher"); LR = M("LessonRequirement")
        TFA = M("TeacherFreeAfternoon"); TA = M("TeacherAvailability")
        Per = M("Period")

        code = kw["code"]
        t = (
            Teacher.objects.filter(employee_code=code).first()
            or Teacher.objects.filter(teacher_number=code).first()
        )
        if not t:
            print(f"{code} not found. Available:")
            for x in Teacher.objects.all()[:40]:
                print("  ", getattr(x,"employee_code",None), "|", getattr(x,"teacher_number",None), "|", str(x))
            return

        print(f"Teacher: pk={t.pk} employee_code={getattr(t,'employee_code',None)} number={getattr(t,'teacher_number',None)} name={t}")
        print()
        reqs = LR.objects.filter(teacher=t, is_active=True).select_related("subject","instructional_group")
        total = 0
        print("=== Active lesson requirements ===")
        for r in reqs.order_by("instructional_group__name","subject__code"):
            ig = r.instructional_group.name if r.instructional_group else "?"
            sub = r.subject.code if r.subject else "?"
            print(f"  {ig:14s} {sub:8s} n={r.lessons_per_week}")
            total += r.lessons_per_week
        print(f"  TOTAL required: {total}")
        print()

        fa = list(TFA.objects.filter(teacher=t, is_active=True))
        print(f"=== Free afternoons: {len(fa)} ===")
        for f in fa: print(f"  id={f.pk} day={f.day}")
        print()

        ta = TA.objects.filter(teacher=t, is_active=True)
        unavail = [x for x in ta if not x.is_available]
        print(f"=== Unavailability overrides: {len(unavail)} ===")
        for a in unavail[:20]: print(f"  {a.day} period={a.period_id}")
        print()

        tp = Per.objects.filter(is_teaching_period=True).count() or 10
        raw = tp * 5
        blocked_fa = len(fa) * 3
        avail = raw - blocked_fa - len(unavail)
        print(f"=== Capacity ===")
        print(f"  raw weekly slots : {raw}")
        print(f"  - free afternoons: {blocked_fa}")
        print(f"  - unavailability : {len(unavail)}")
        print(f"  = available      : {avail}")
        print(f"  required         : {total}")
        deficit = total - avail
        print(f"  DEFICIT          : {deficit}")
        print()

        if deficit <= 0:
            print(">> OK: capacity fine.")
            return

        print(f">> INFEASIBLE: need {deficit} more slots.")
        if kw["apply"]:
            freed = 0
            for f in fa:
                if freed >= deficit: break
                print(f"FIX: deactivate free-afternoon id={f.pk} day={f.day}")
                f.is_active = False
                f.save(update_fields=["is_active"])
                freed += 3
            print(f"  freed ~{freed} slots")
        else:
            print("Dry run. Add --apply to fix.")
