from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

BLOCKS = {
    "OPTION_1": {"COMP", "CHEM"},
    "OPTION_2": {"BIO", "GEO", "HIS"},
    "OPTION_3": {"PHY", "LIT", "MUSD"},
    "OPTION_4": {"AGR", "BUS"},
}

class Command(BaseCommand):
    help = "Verify Option C: all block subjects at every block slot"
    def handle(self, *a, **kw):
        TV = M("TimetableVersion")
        latest = TV.objects.order_by("-version_number").first()
        print(f"Version: #{latest.version_number} id={latest.pk}\n")

        entries = list(latest.entries.select_related(
            "instructional_group", "lesson_requirement__subject", "teacher", "room"
        ).all())
        print(f"Total entries: {len(entries)}\n")

        # Count per group
        from collections import Counter
        per_group = Counter(e.instructional_group.name for e in entries if e.instructional_group)
        print("=== Entries per group ===")
        for g in sorted(per_group):
            print(f"  {g:12s} {per_group[g]}")

        # For each grade, verify block subjects appear at every slot
        for grade in ("Grade 10E", "Grade 10W", "Grade 11E", "Grade 11W"):
            print(f"\n=== {grade}: block subjects per slot ===")
            group_entries = [e for e in entries if e.instructional_group and e.instructional_group.name == grade]
            # Group by (day, period) -> set of block subjects
            slots = defaultdict(set)
            for e in group_entries:
                subj = getattr(getattr(e.lesson_requirement, "subject", None), "code", None)
                if e.lesson_requirement.requirement_type != "BLOCK":
                    continue
                slots[(e.day, str(e.period_id)[:8])].add(subj)

            for key in sorted(slots):
                subjects = sorted(slots[key])
                print(f"  {key[0]} p={key[1]}  {subjects}")
