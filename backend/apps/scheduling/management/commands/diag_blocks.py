from django.core.management.base import BaseCommand
from collections import defaultdict
from apps.scheduling.models import (
    TimetableEntry, TimetableVersion, LessonRequirement, InstructionalGroup
)


class Command(BaseCommand):
    help = "Forensic deep-dive: why placed > req"

    def add_arguments(self, parser):
        parser.add_argument("--ver", type=int, default=None)
        parser.add_argument("--class-name", type=str, default="G11E")

    def handle(self, *args, **opts):
        ver = (TimetableVersion.objects.filter(version_number=opts["ver"]).first()
               if opts["ver"] else TimetableVersion.objects.order_by("-created_at").first())
        print(f"Version: {ver}")

        print("\n-- LessonRequirement fields --")
        for f in LessonRequirement._meta.get_fields():
            if hasattr(f, "get_internal_type"):
                print(f"  {f.name} ({f.get_internal_type()})")

        print("\n-- InstructionalGroup fields --")
        for f in InstructionalGroup._meta.get_fields():
            if hasattr(f, "get_internal_type"):
                print(f"  {f.name} ({f.get_internal_type()})")

        cls = opts["class_name"]
        rows = list(TimetableEntry.objects
                    .filter(timetable_version=ver)
                    .select_related("period", "instructional_group", "lesson_requirement"))
        print(f"\nTotal rows in version: {len(rows)}")

        by_ig = defaultdict(list)
        for r in rows:
            by_ig[str(r.instructional_group)].append(r)

        print(f"\nInstructional groups ({len(by_ig)}):")
        for name in sorted(by_ig):
            print(f"  {name}  ({len(by_ig[name])} rows)")

        target_rows = [r for r in rows if cls in str(r.instructional_group)]
        if not target_rows:
            print(f"\nNo rows match class ~ '{cls}'")
            return
        print(f"\nRows matching '{cls}': {len(target_rows)}")

        groups = defaultdict(list)
        for r in target_rows:
            lr = r.lesson_requirement
            subj_obj = getattr(lr, "subject", None)
            subj = getattr(subj_obj, "code", None) or str(subj_obj)
            groups[(str(r.instructional_group), subj)].append(r)

        print(f"\n{'IG':45} {'SUBJ':10} rows")
        print("-" * 70)
        for (ig, subj), rs in sorted(groups.items()):
            print(f"{ig:45} {subj:10} {len(rs):4}")

        print("\n-- Sample LessonRequirement objects (up to 3) --")
        seen = set()
        for r in target_rows:
            lr = r.lesson_requirement
            if lr.pk in seen:
                continue
            seen.add(lr.pk)
            print(f"\n  {lr}")
            for f in LessonRequirement._meta.get_fields():
                if hasattr(f, "get_internal_type") and not f.auto_created:
                    try:
                        val = getattr(lr, f.name)
                    except Exception as e:
                        val = f"<err {e}>"
                    print(f"    {f.name:25} = {val!r}")
            if len(seen) >= 3:
                break
