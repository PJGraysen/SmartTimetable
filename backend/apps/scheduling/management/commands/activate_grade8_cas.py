from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        LR = M("LessonRequirement"); IG = M("InstructionalGroup"); SUBJ = M("Subject")
        cas = SUBJ.objects.filter(code="CAS").first()
        for gname in ("Grade 8E","Grade 8W"):
            ig = IG.objects.filter(name=gname).first()
            r = LR.objects.filter(instructional_group=ig, subject=cas).first()
            if not r:
                print(f"{gname}: no CAS requirement"); continue
            if r.is_active:
                print(f"{gname}: already active"); continue
            print(f"{gname}: CAS n={r.lessons_per_week} -> activate")
            if kw["apply"]:
                with transaction.atomic():
                    r.is_active = True
                    r.save(update_fields=["is_active"])
        print("Applied." if kw["apply"] else "Dry run — add --apply.")
