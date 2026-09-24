from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    help = "Add CAS (5/wk) to Grade 8E and Grade 8W"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        LR = M("LessonRequirement"); IG = M("InstructionalGroup"); SUBJ = M("Subject")
        Term = M("Term")

        subj = SUBJ.objects.filter(code="CAS").first()
        if not subj:
            print("CAS subject row does not exist. Create it first."); return

        term = Term.objects.filter(is_active=True).first() or Term.objects.first()

        for gname in ("Grade 8E","Grade 8W"):
            ig = IG.objects.filter(name=gname).first()
            if not ig: print(f"{gname} not found"); continue

            existing = LR.objects.filter(instructional_group=ig, subject=subj).first()
            if existing:
                print(f"{gname} already has CAS (n={existing.lessons_per_week}, active={existing.is_active})")
                continue

            print(f"{gname}: would add CAS 5/wk, term={term}")
            if kw["apply"]:
                with transaction.atomic():
                    LR.objects.create(
                        instructional_group=ig,
                        subject=subj,
                        term=term,
                        lessons_per_week=5,
                        requirement_type="STANDALONE",
                        is_active=True,
                    )
                    print(f"  -> created")

        print()
        print("Dry run. Add --apply to persist." if not kw["apply"] else "Applied.")
