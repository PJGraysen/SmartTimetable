from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict


def M(n):
    for m in apps.get_models():
        if m.__name__ == n:
            return m


class Command(BaseCommand):
    help = "Audit: count distinct (day, period) slots per teacher, not entries."

    def handle(self, *a, **kw):
        TV = M("TimetableVersion")
        TE = M("TimetableEntry")

        ver = TV.objects.order_by("-version_number").first()
        print(f"=== Teacher load (distinct slots)  v{ver.version_number} {ver.name} ===\n")

        slots = defaultdict(set)
        for e in TE.objects.filter(timetable_version=ver).select_related("teacher", "period"):
            if not e.teacher:
                continue
            key = (e.day, getattr(e.period, "number", e.period_id))
            slots[e.teacher.employee_code].add(key)

        loads = sorted(((code, len(s)) for code, s in slots.items()),
                       key=lambda x: -x[1])

        for code, n in loads:
            flag = "  *** OVER 46 ***" if n > 46 else ""
            print(f"  {code:6s}  {n:3d}{flag}")

        over = [f"{c}={n}" for c, n in loads if n > 46]
        print()
        print(f"Teachers over 46: {over if over else 'NONE'}")
        print(f"Max load: {loads[0] if loads else 'n/a'}")
