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
    help = "Check 11E/11W block subjects occupy identical physical slots"
    def handle(self, *a, **kw):
        TV = M("TimetableVersion")
        latest = TV.objects.order_by("-version_number").first()
        entries = latest.entries.select_related(
            "instructional_group", "lesson_requirement__subject"
        ).all()

        # (subj_code, day, period_id) -> set of group names
        slots = defaultdict(set)
        for e in entries:
            subj = getattr(getattr(e.lesson_requirement, "subject", None), "code", None)
            g = getattr(getattr(e, "instructional_group", None), "name", "?")
            if not subj or g not in {"Grade 11E", "Grade 11W", "Grade 10E", "Grade 10W"}:
                continue
            slots[(subj, e.day, e.period_id)].add(g)

        print("=== Grade 11E vs 11W: BLOCK subjects on identical slots ===")
        any_fail = False
        for block, subjects in BLOCKS.items():
            for subj in sorted(subjects):
                e_slots = {k for k, gs in slots.items() if k[0] == subj and "Grade 11E" in gs}
                w_slots = {k for k, gs in slots.items() if k[0] == subj and "Grade 11W" in gs}
                shared = e_slots & w_slots
                only_e = e_slots - w_slots
                only_w = w_slots - e_slots
                if not e_slots and not w_slots:
                    mark = "—"
                elif not only_e and not only_w:
                    mark = "✅"
                else:
                    mark = "❌"
                    any_fail = True
                print(f"  {mark} {block:8s} {subj:5s} E={len(e_slots)} W={len(w_slots)} shared={len(shared)} onlyE={len(only_e)} onlyW={len(only_w)}")

        print()
        print("=== Grade 10E vs 10W: same check (baseline) ===")
        for block, subjects in BLOCKS.items():
            for subj in sorted(subjects):
                e_slots = {k for k, gs in slots.items() if k[0] == subj and "Grade 10E" in gs}
                w_slots = {k for k, gs in slots.items() if k[0] == subj and "Grade 10W" in gs}
                if not e_slots and not w_slots:
                    mark = "—"
                elif e_slots == w_slots:
                    mark = "✅"
                else:
                    mark = "❌"
                    any_fail = True
                print(f"  {mark} {block:8s} {subj:5s} E={len(e_slots)} W={len(w_slots)} shared={len(e_slots & w_slots)}")

        print()
        print("OVERALL:", "❌ FAIL" if any_fail else "✅ all synchronous")
