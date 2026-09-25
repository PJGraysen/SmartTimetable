from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    help = "Setup GST subject + inactive requirements for filler entries"
    def handle(self, *a, **kw):
        Subject = M("Subject")
        LR = M("LessonRequirement")
        IG = M("InstructionalGroup")
        Term = M("Term")

        subj = Subject.objects.filter(code="GST").first()
        if not subj:
            subj = Subject.objects.create(code="GST", name="Group Study", is_active=True)
            print("Created Subject GST")

        term = Term.objects.filter(is_active=True).first() or Term.objects.first()
        if not term:
            print("ABORT: no Term found"); return

        n_created = 0
        for ig in IG.objects.filter(is_active=True):
            exists = LR.objects.filter(instructional_group=ig, subject=subj).first()
            if exists:
                # Normalize: ensure it is inactive so solver ignores it
                if exists.is_active:
                    exists.is_active = False
                    exists.save(update_fields=["is_active"])
                print(f"  {ig.name}: GST LR exists (id={str(exists.pk)[:8]}, inactive)")
                continue
            with transaction.atomic():
                LR.objects.create(
                    instructional_group=ig,
                    subject=subj,
                    term=term,
                    lessons_per_week=1,   # constraint requires >0
                    requirement_type="STANDALONE",
                    is_active=False,      # solver skips it
                )
            print(f"  {ig.name}: created inactive GST LR")
            n_created += 1
        print()
        print(f"Created {n_created} GST requirement(s)")
