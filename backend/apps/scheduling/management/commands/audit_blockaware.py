from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict, Counter


def M(n):
    for m in apps.get_models():
        if m.__name__ == n:
            return m


class Command(BaseCommand):
    help = "Audit: count each TimetableEntry row once, per (IG, subject)."

    def handle(self, *a, **kw):
        TV = M("TimetableVersion")
        TE = M("TimetableEntry")
        LR = M("LessonRequirement")

        latest = TV.objects.order_by("-version_number").first()
        if latest is None:
            self.stderr.write("No TimetableVersion")
            return
        print(f"Latest: v{latest.version_number} {latest.name}\n")

        placed = defaultdict(Counter)
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

        required = defaultdict(Counter)
        for r in LR.objects.filter(is_active=True).select_related(
            "instructional_group", "subject"
        ):
            ig = r.instructional_group.name if r.instructional_group else "?"
            subj = r.subject.code if r.subject else "?"
            required[ig][subj] += r.lessons_per_week

        any_bad = False
        for ig in sorted(required.keys()):
            req_total = sum(required[ig].values())
            plc_total = sum(placed[ig].values())
            mismatch = (req_total != plc_total) or any(
                required[ig].get(s, 0) != placed[ig].get(s, 0)
                for s in set(required[ig]) | set(placed[ig])
            )
            tag = "MISMATCH" if mismatch else "OK"
            if mismatch:
                any_bad = True
            print(f"== {ig} ==   req={req_total}  placed={plc_total}  {tag}")
            for subj in sorted(set(required[ig]) | set(placed[ig])):
                req = required[ig].get(subj, 0)
                plc = placed[ig].get(subj, 0)
                mark = "OK  " if req == plc else ("MISS" if plc < req else "EXTR")
                print(f"   {mark}  {subj:8s} req={req:2d}  placed={plc:2d}")
            print()

        print("RESULT:", "MISMATCHES FOUND" if any_bad else "ALL CLASSES OK")
