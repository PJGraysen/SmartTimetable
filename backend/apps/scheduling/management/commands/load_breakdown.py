from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict
import re

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

def grade_base(name):
    return re.sub(r"\s*[EW]\s*$", "", name).strip()

class Command(BaseCommand):
    help = "Per-teacher load, collapsing shared BLOCK electives (raw vs real)"
    def handle(self, *a, **kw):
        LR = M("LessonRequirement"); Teacher = M("Teacher")

        lrs = LR.objects.filter(is_active=True).select_related(
            "teacher", "instructional_group", "subject"
        )

        grouped = defaultdict(lambda: defaultdict(list))
        for r in lrs:
            if not r.teacher_id or not r.instructional_group_id or not r.subject:
                continue
            gname = r.instructional_group.name
            key = (grade_base(gname), r.subject.code, r.requirement_type)
            grouped[r.teacher_id][key].append({
                "group": gname,
                "lpw": r.lessons_per_week,
                "is_block": r.requirement_type == "BLOCK",
            })

        raw = defaultdict(int); real = defaultdict(int)
        detail = defaultdict(list)

        for tid, groups in grouped.items():
            for (gb, subj, rtype), items in groups.items():
                if rtype == "BLOCK":
                    lpw = items[0]["lpw"]
                    streams = sorted(set(i["group"] for i in items))
                    raw[tid] += sum(i["lpw"] for i in items)
                    real[tid] += lpw
                    detail[tid].append((f"{gb} [BLOCK]", subj, lpw, streams))
                else:
                    for i in items:
                        raw[tid] += i["lpw"]; real[tid] += i["lpw"]
                        detail[tid].append((i["group"], subj, i["lpw"], [i["group"]]))

        print(f"{'Code':6s} {'Name':26s} {'Raw':>4s} {'Real':>5s}  Breakdown")
        print("-" * 110)
        for t in Teacher.objects.filter(is_active=True).order_by("employee_code"):
            rw = raw.get(t.pk, 0); rl = real.get(t.pk, 0)
            if rl == 0:
                print(f"{t.employee_code:6s} {str(t)[:26]:26s} {rw:4d} {rl:5d}  (no load)")
                continue
            marker = "  <<< OVER" if rl > 46 else ("  (near cap)" if rl >= 42 else "")
            delta = f"  Δ-{rw-rl}" if rw != rl else ""
            print(f"{t.employee_code:6s} {str(t)[:26]:26s} {rw:4d} {rl:5d}{marker}{delta}")
            for label, subj, lpw, streams in sorted(detail[t.pk]):
                via = ", ".join(streams)
                print(f"{'':6s} {'':26s} {'':4s} {'':5s}    {label:22s} {lpw:2d}  [{subj}]  via {via}")

        print("-" * 110)
        print(f"Grand total raw:       {sum(raw.values())}")
        print(f"Grand total effective: {sum(real.values())}")
