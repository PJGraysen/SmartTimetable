from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Definitively remove GST: entries -> LRs -> subject"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        Subject = M("Subject")
        LR = M("LessonRequirement")
        TE = M("TimetableEntry")

        gst = Subject.objects.filter(code="GST").first()
        if not gst:
            print("No GST subject in DB — nothing to remove")
            return

        lr_qs = LR.objects.filter(subject__code="GST")
        lr_ids = list(lr_qs.values_list("id", flat=True))
        te_qs = TE.objects.filter(lesson_requirement_id__in=lr_ids)

        print(f"Subject GST: pk={gst.pk} name={gst.name!r}")
        print(f"  LessonRequirements: {lr_qs.count()}")
        print(f"  TimetableEntries:   {te_qs.count()}")
        print()
        print("Per-class breakdown of GST LRs:")
        for lr in lr_qs:
            ig = lr.instructional_group.name if lr.instructional_group else "?"
            print(f"  {ig:14s} active={lr.is_active}  n={lr.lessons_per_week}  pk={str(lr.pk)[:8]}")

        if not kw["apply"]:
            print()
            print("Dry run. Add --apply to delete all of the above.")
            return

        with transaction.atomic():
            n_te = te_qs.delete()[0]
            n_lr = lr_qs.delete()[0]
            n_s = Subject.objects.filter(code="GST").delete()[0]
        print()
        print(f"Deleted: {n_te} entries, {n_lr} LRs, {n_s} subject(s)")

        # Verify nothing remains
        print()
        print("Verify (should all be 0):")
        print(f"  Subject GST remaining:         {Subject.objects.filter(code='GST').count()}")
        print(f"  LessonRequirement GST:         {LR.objects.filter(subject__code='GST').count()}")
