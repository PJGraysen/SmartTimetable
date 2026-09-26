from django.core.management.base import BaseCommand
from pathlib import Path
import re

class Command(BaseCommand):
    help = "Show auto-fill hook + latest versions + fill test"
    def handle(self, *a, **kw):
        from apps.scheduling.models import TimetableVersion, TimetableEntry

        print("=" * 70)
        print("1. AUTO-FILL HOOK context in views.py")
        print("=" * 70)
        vp = Path("apps/scheduling/api/views.py")
        vsrc = vp.read_text(encoding="utf-8")
        idx = vsrc.find("Auto-fill empty cells")
        if idx == -1:
            print("  NOT FOUND — hook was never inserted")
        else:
            start = vsrc.rfind("\n", 0, idx - 200)
            end = vsrc.find("\n\n", idx)
            print(vsrc[start if start != -1 else 0:end if end != -1 else idx+500])

        print()
        print("=" * 70)
        print("2. Recent versions + entry counts")
        print("=" * 70)
        for v in TimetableVersion.objects.order_by("-version_number")[:6]:
            n = TimetableEntry.objects.filter(timetable_version=v).count()
            gst = TimetableEntry.objects.filter(
                timetable_version=v,
                lesson_requirement__subject__code="GST"
            ).count()
            print(f"  v{v.version_number:5d}  id={str(v.pk)[:8]}  entries={n:4d}  gst={gst:3d}  {v.name}")

        print()
        print("=" * 70)
        print("3. Latest run statuses")
        print("=" * 70)
        from apps.scheduling.models import SchedulingRun
        for r in SchedulingRun.objects.order_by("-created_at")[:5]:
            print(f"  {r.status:12s}  id={str(r.pk)[:8]}  version={(r.timetable_version.version_number if r.timetable_version else None)}  err={(r.error_message or '')[:80]}")
