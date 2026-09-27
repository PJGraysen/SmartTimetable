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
    help = "Dump every entry in block slots for Grade 10E/10W and 11E/11W"
    def handle(self, *a, **kw):
        TV = M("TimetableVersion")
        latest = TV.objects.order_by("-version_number").first()
        entries = list(latest.entries.select_related(
            "instructional_group", "lesson_requirement__subject",
            "teacher", "room"
        ).all())

        wanted = {"Grade 10E", "Grade 10W", "Grade 11E", "Grade 11W"}
        by_slot = defaultdict(list)
        for e in entries:
            g = getattr(getattr(e, "instructional_group", None), "name", "?")
            if g not in wanted: continue
            subj = getattr(getattr(e.lesson_requirement, "subject", None), "code", "")
            rt = getattr(e.lesson_requirement, "requirement_type", "")
            if rt != "BLOCK": continue
            key = (e.day, str(e.period_id))
            by_slot[key].append({
                "group": g, "subj": subj,
                "teacher": str(e.teacher) if e.teacher else "—",
                "room": str(e.room) if e.room else "—",
            })

        # For each of the four grades, print each slot with its block subjects
        for grade_pair in (("Grade 10E", "Grade 10W"), ("Grade 11E", "Grade 11W")):
            print(f"\n========== {grade_pair[0]} / {grade_pair[1]} block slots ==========")
            pairs = defaultdict(lambda: {"Grade 10E":[], "Grade 10W":[], "Grade 11E":[], "Grade 11W":[]})
            for key, rows in by_slot.items():
                for r in rows:
                    if r["group"] in grade_pair:
                        pairs[key][r["group"]].append(r)

            for key in sorted(pairs):
                rows = pairs[key]
                if not any(rows.values()): continue
                print(f"\n  SLOT day={key[0]} period={key[1][:8]}")
                for g in grade_pair:
                    if not rows[g]:
                        print(f"    {g:11s} (no BLOCK entry)")
                        continue
                    for r in rows[g]:
                        print(f"    {g:11s} {r['subj']:5s} teacher={r['teacher']:28s} room={r['room']}")
