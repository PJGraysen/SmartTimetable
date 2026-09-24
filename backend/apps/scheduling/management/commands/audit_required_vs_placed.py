from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict, Counter

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    help = "Per-class: required vs placed vs missing vs empty cells"
    def handle(self, *a, **kw):
        TV = M("TimetableVersion"); TE = M("TimetableEntry")
        LR = M("LessonRequirement"); IG = M("InstructionalGroup")

        latest = TV.objects.order_by("-version_number").first()
        if not latest:
            print("no versions"); return
        print(f"Latest version: v{latest.version_number} {latest.name}")
        print()

        # placed per class per subject
        placed = defaultdict(Counter)
        total_placed = defaultdict(int)
        for e in TE.objects.filter(timetable_version=latest).select_related(
            "instructional_group", "lesson_requirement__subject"
        ):
            ig = e.instructional_group.name if e.instructional_group else "?"
            subj = (
                e.lesson_requirement.subject.code
                if e.lesson_requirement and e.lesson_requirement.subject
                else "?"
            )
            placed[ig][subj] += 1
            total_placed[ig] += 1

        # required per class per subject
        required = defaultdict(Counter)
        for r in LR.objects.filter(is_active=True).select_related(
            "instructional_group", "subject"
        ):
            ig = r.instructional_group.name if r.instructional_group else "?"
            subj = r.subject.code if r.subject else "?"
            required[ig][subj] += r.lessons_per_week

        for ig_name in sorted(required.keys()):
            req_total = sum(required[ig_name].values())
            plc_total = total_placed.get(ig_name, 0)
            print(f"== {ig_name} ==")
            print(f"   required: {req_total} lessons   placed: {plc_total}   empty cells: {50 - plc_total}")

            for subj in sorted(set(required[ig_name]) | set(placed[ig_name])):
                req = required[ig_name].get(subj, 0)
                plc = placed[ig_name].get(subj, 0)
                if req == plc:
                    mark = "OK  "
                elif plc < req:
                    mark = "MISS"
                else:
                    mark = "EXTRA"
                print(f"   {mark}  {subj:8s} req={req:2d}  placed={plc:2d}")
            print()

        print("=== GRAND TOTAL ===")
        print(f"  required: {sum(sum(c.values()) for c in required.values())}")
        print(f"  placed  : {sum(total_placed.values())}")
        print(f"  empty   : {8 * 50 - sum(total_placed.values())} cells across 8 classes × 50 periods")
