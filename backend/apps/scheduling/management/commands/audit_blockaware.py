from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict, Counter

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Audit that treats parallel blocks as single units (correct semantics)"
    def handle(self, *a, **kw):
        TV = M("TimetableVersion"); TE = M("TimetableEntry")
        LR = M("LessonRequirement")
        from apps.scheduling.engine.application.grade10_parallel_blocks import (
            get_grade10_parallel_block_for_subject,
            get_senior_school_block_for_subject,
            is_grade10_instructional_group,
            is_senior_school_instructional_group,
        )

        latest = TV.objects.order_by("-version_number").first()
        print(f"Latest: v{latest.version_number} {latest.name}")
        print()

        # Placed per class: count each BLOCK SLOT as all members
        placed = defaultdict(Counter)
        for e in TE.objects.filter(timetable_version=latest).select_related(
            "instructional_group", "lesson_requirement__subject"
        ):
            ig_obj = e.instructional_group
            ig = ig_obj.name if ig_obj else "?"
            subj = (
                e.lesson_requirement.subject.code
                if e.lesson_requirement and e.lesson_requirement.subject
                else "?"
            )
            # check if this subject is a block member
            block = None
            if is_grade10_instructional_group(ig_obj):
                block = get_grade10_parallel_block_for_subject(subj)
            elif is_senior_school_instructional_group(ig_obj):
                block = get_senior_school_block_for_subject(subj)
            if block is not None:
                for code in block.subject_codes:
                    placed[ig][str(code).upper()] += 1
            else:
                placed[ig][subj] += 1

        # Required per class
        required = defaultdict(Counter)
        for r in LR.objects.filter(is_active=True).select_related(
            "instructional_group", "subject"
        ):
            ig = r.instructional_group.name if r.instructional_group else "?"
            subj = r.subject.code if r.subject else "?"
            required[ig][subj] += r.lessons_per_week

        for ig in sorted(required.keys()):
            req_total = sum(required[ig].values())
            plc_total = sum(placed[ig].values())
            print(f"== {ig} ==")
            print(f"   required: {req_total}   placed(block-aware): {plc_total}")
            for subj in sorted(set(required[ig]) | set(placed[ig])):
                req = required[ig].get(subj, 0)
                plc = placed[ig].get(subj, 0)
                mark = "OK  " if req == plc else ("MISS" if plc < req else "EXTR")
                print(f"   {mark}  {subj:8s} req={req:2d}  placed={plc:2d}")
            print()
