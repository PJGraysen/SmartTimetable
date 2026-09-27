from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Create TeacherAssignment rows for Grade 11 (mirrors LR.teacher FK)"
    def add_arguments(self, p):
        p.add_argument("--commit", action="store_true")
        p.add_argument("--groups", nargs="+", default=["Grade 11E", "Grade 11W"])

    def handle(self, *a, **kw):
        IG = M("InstructionalGroup"); LR = M("LessonRequirement")
        TA = M("TeacherAssignment")

        plan = []
        for gname in kw["groups"]:
            g = IG.objects.filter(name=gname).first()
            if not g:
                print(f"  {gname}: NOT FOUND"); continue
            for lr in LR.objects.filter(instructional_group=g, is_active=True).select_related("subject", "teacher"):
                existing = TA.objects.filter(lesson_requirement=lr).first()
                if existing:
                    continue
                plan.append((gname, lr))

        print(f"{'Group':12s} {'Subject':8s} {'Teacher':8s} Action")
        print("-" * 50)
        for gname, lr in plan:
            tcode = lr.teacher.employee_code if lr.teacher else "NONE"
            action = "CREATE" if lr.teacher else "SKIP (no teacher on LR)"
            print(f"{gname:12s} {lr.subject.code:8s} {tcode:8s} {action}")

        creatable = [x for x in plan if x[1].teacher_id]
        print(f"\nTotal LRs without TA: {len(plan)}")
        print(f"With teacher on LR:   {len(creatable)}")

        if not kw["commit"]:
            print("\nDRY RUN — pass --commit to write")
            return

        with transaction.atomic():
            created = 0
            for gname, lr in creatable:
                TA.objects.create(
                    teacher=lr.teacher,
                    lesson_requirement=lr,
                    is_active=True,
                )
                created += 1
            print(f"\nCreated {created} TeacherAssignment rows")
