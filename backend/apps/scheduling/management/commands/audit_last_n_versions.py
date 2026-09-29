from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict, Counter


def M(n):
    for m in apps.get_models():
        if m.__name__ == n:
            return m
    raise LookupError(n)


class Command(BaseCommand):
    help = "Audit last N versions: requirement compliance + blank cells + teacher load"

    def add_arguments(self, p):
        p.add_argument("--versions", type=int, default=5)

    def handle(self, *a, **kw):
        TV = M("TimetableVersion")
        TE = M("TimetableEntry")
        LR = M("LessonRequirement")
        IG = M("InstructionalGroup")
        Per = M("Period")
        Teacher = M("Teacher")
        TA = M("TeacherAssignment")

        teaching_periods = set(
            str(p.pk) for p in Per.objects.filter(is_teaching_period=True, number__lte=10)
        )
        all_classes = list(IG.objects.filter(is_active=True).order_by("name"))

        required = defaultdict(Counter)
        for r in LR.objects.filter(is_active=True).select_related(
            "instructional_group", "subject"
        ):
            ig_name = r.instructional_group.name if r.instructional_group else "?"
            subj = r.subject.code if r.subject else "?"
            required[ig_name][subj] += r.lessons_per_week

        versions = list(TV.objects.order_by("-version_number")[: kw["versions"]])
        if not versions:
            print("No versions found")
            return

        for v in versions:
            print("=" * 78)
            print(f"VERSION v{v.version_number}  id={str(v.pk)[:8]}  {v.name}")
            print("=" * 78)

            entries = list(
                TE.objects.filter(timetable_version=v).select_related(
                    "instructional_group", "lesson_requirement__subject"
                )
            )

            placed = defaultdict(Counter)
            filled_keys = set()
            for e in entries:
                ig_obj = e.instructional_group
                ig_name = ig_obj.name if ig_obj else "?"
                subj = (
                    e.lesson_requirement.subject.code
                    if e.lesson_requirement and e.lesson_requirement.subject
                    else "?"
                )
                placed[ig_name][subj] += 1
                if e.period_id:
                    filled_keys.add(
                        (
                            str(e.instructional_group_id),
                            str(e.day or "").upper(),
                            str(e.period_id),
                        )
                    )

            for ig in all_classes:
                ig_name = ig.name
                req = required.get(ig_name, Counter())
                plc = placed.get(ig_name, Counter())

                req_total = sum(req.values())
                plc_total = sum(plc.values())

                empty = 0
                for day in ("MON", "TUE", "WED", "THU", "FRI"):
                    for pid in teaching_periods:
                        if (str(ig.pk), day, pid) not in filled_keys:
                            empty += 1

                mism = []
                for subj in sorted(set(req) | set(plc)):
                    rq = req.get(subj, 0)
                    pq = plc.get(subj, 0)
                    if rq != pq:
                        mism.append(f"{subj}:req{rq}/pl{pq}")

                status = "OK " if not mism else "MISMATCH"
                print(
                    f"  {ig_name:14s} req={req_total:3d}  placed={plc_total:3d}  "
                    f"empty={empty:3d}  {status}"
                )
                for m in mism:
                    print(f"      {m}")

            loads = []
            for t in Teacher.objects.filter(is_active=True):
                total = sum(
                    ta.lesson_requirement.lessons_per_week
                    for ta in TA.objects.filter(
                        teacher=t, is_active=True
                    ).select_related("lesson_requirement")
                    if ta.lesson_requirement
                )
                if total > 0:
                    loads.append((t.employee_code, total))
            if loads:
                loads.sort(key=lambda x: -x[1])
                top3 = ", ".join(f"{c}={n}" for c, n in loads[:3])
                print(f"  TEACHER LOADS top3 (row count, see audit_teacher_slots): {top3}")
            print()
