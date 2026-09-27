from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Count assignments per instructional group in the newest timetable version"
    def handle(self, *a, **kw):
        TV = M("TimetableVersion")
        latest = TV.objects.order_by("-version_number").first()
        if not latest:
            print("No TimetableVersion rows found."); return
        print(f"Latest version: #{latest.version_number}  id={latest.pk}  name={getattr(latest,'name','?')}")

        # Try to find assignment rows via the version's reverse FK
        for related_name in ("assignments", "entries", "timetable_entries", "slots"):
            if hasattr(latest, related_name):
                qs = getattr(latest, related_name).all()
                counter = defaultdict(int)
                for a in qs:
                    g = getattr(getattr(a, "instructional_group", None), "name", "?")
                    counter[g] += 1
                print(f"\nPer-group assignment counts (via {related_name}):")
                for g in sorted(counter):
                    print(f"  {g:12s} {counter[g]}")
                return
        print("Could not find the assignment related_name on TimetableVersion.")
        print("Fields:", [f.name for f in latest._meta.get_fields()])
