from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Dump the fields on a Grade 11 entry so we know how to read it"
    def handle(self, *a, **kw):
        TV = M("TimetableVersion")
        latest = TV.objects.order_by("-version_number").first()
        print(f"Version: #{latest.version_number} id={latest.pk}")

        # Find the entry model from the related manager
        entries_qs = getattr(latest, "entries").all()
        print(f"Total entries: {entries_qs.count()}")
        print()

        sample = entries_qs.first()
        print("=== Fields on one entry ===")
        for f in sample._meta.get_fields():
            if hasattr(f, "attname"):
                val = getattr(sample, f.attname, None)
                print(f"  {f.name:30s} = {str(val)[:60]}")
            else:
                print(f"  {f.name:30s} (relation)")

        print()
        print("=== Distinct instructional_groups on entries ===")
        from collections import Counter
        igs = Counter()
        for e in entries_qs:
            ig = getattr(getattr(e, "instructional_group", None), "name", "?")
            igs[ig] += 1
        for name, count in igs.most_common():
            print(f"  {name:12s} {count}")
        print()

        print("=== 5 sample Grade 11E entries ===")
        shown = 0
        for e in entries_qs:
            ig_name = getattr(getattr(e, "instructional_group", None), "name", None)
            if ig_name == "Grade 11E":
                print(f"  id={e.pk}")
                # Try every conceivable subject access
                for attr in ("subject", "subject_code", "lesson_requirement", "requirement"):
                    v = getattr(e, attr, None)
                    if v is not None:
                        print(f"    {attr} = {v}")
                print(f"    day = {getattr(e, 'day', None)}")
                print(f"    period = {getattr(e, 'period', None)}")
                shown += 1
                if shown >= 5: break
