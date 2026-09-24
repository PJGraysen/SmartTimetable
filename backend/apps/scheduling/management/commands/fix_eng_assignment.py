from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    help = "Reassign Form 4E/4W English from T011 to Madam Maryann (T015)"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        Teacher = M("Teacher"); LR = M("LessonRequirement")

        print("=== All teachers ===")
        for t in Teacher.objects.all().order_by("employee_code"):
            print(f"  {getattr(t,'employee_code',None)!s:6s} | {getattr(t,'teacher_number',None)!s:4s} | {t.first_name} {t.last_name} | {str(t)}")

        # find T011 and T015
        t11 = Teacher.objects.filter(employee_code="T011").first()
        t15 = Teacher.objects.filter(employee_code="T015").first()

        if t15 is None:
            # try by name
            t15 = (
                Teacher.objects.filter(last_name__icontains="maryann").first()
                or Teacher.objects.filter(first_name__icontains="maryann").first()
                or Teacher.objects.filter(last_name__icontains="mary").first()
            )
        if t15 is None:
            print("\n!! T015 (Madam Maryann) not found. Cannot proceed.")
            print("   Add her teacher record first, then rerun.")
            return

        print(f"\nT011 = pk={t11.pk if t11 else None} {t11}")
        print(f"T015 = pk={t15.pk} {t15}")

        # find all currently-T011 requirements whose group is Form 4E or Form 4W
        to_move = LR.objects.filter(
            teacher=t11,
            is_active=True,
            instructional_group__name__in=["Form 4E", "Form 4W"],
            subject__code="ENG",
        ).select_related("instructional_group","subject")

        print(f"\n=== Requirements to reassign: {to_move.count()} ===")
        for r in to_move:
            print(f"  {r.instructional_group.name} {r.subject.code} n={r.lessons_per_week} teacher_now={r.teacher}")

        if not kw["apply"]:
            print("\nDry run. Add --apply to persist.")
            return

        with transaction.atomic():
            n = 0
            for r in to_move:
                r.teacher = t15
                r.save(update_fields=["teacher"])
                n += 1
            print(f"\nReassigned {n} requirement(s) from {t11} to {t15}")

        # verify new loads
        print("\n=== New load: T011 ===")
        load11 = sum(r.lessons_per_week for r in LR.objects.filter(teacher=t11, is_active=True))
        print(f"  {load11} lessons/week")
        print("=== New load: T015 ===")
        load15 = sum(r.lessons_per_week for r in LR.objects.filter(teacher=t15, is_active=True))
        print(f"  {load15} lessons/week")

