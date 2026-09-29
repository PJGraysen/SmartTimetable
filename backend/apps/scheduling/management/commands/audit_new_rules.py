from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict


SCIENCE = {"BIO", "CHEM", "PHY"}
PRACTICAL = {"BIOPRAC", "CHEMPRAC", "PHYPRAC"}
MATHS = {"MAT"}
COMPLEX = SCIENCE | MATHS

MATHS_MORNING_CUTOFF = 4  # maths at P5+ is "afternoon"


class Command(BaseCommand):
    help = (
        "Audit complex-subject adjacency + maths-afternoon for the latest (or "
        "a specified) version. Practicals are excluded from the adjacency rule."
    )

    def add_arguments(self, parser):
        parser.add_argument("--ver", type=int, default=None)
        parser.add_argument("--last", type=int, default=0,
                            help="If >0, report for the last N versions.")

    def handle(self, *args, **opts):
        TV = apps.get_model("scheduling", "TimetableVersion")
        TE = apps.get_model("scheduling", "TimetableEntry")

        qs = TV.objects.order_by("-version_number")
        if opts["ver"] is not None:
            qs = qs.filter(version_number=opts["ver"])
        elif opts["last"]:
            qs = qs[: opts["last"]]
        else:
            qs = qs[:1]

        versions = list(qs)
        if not versions:
            self.stderr.write("No versions found.")
            return

        for ver in versions:
            self._audit_version(ver, TE)

    def _audit_version(self, ver, TE):
        print("=" * 78)
        print(f"VERSION v{ver.version_number}  {ver.name}  "
              f"id={str(ver.pk)[:8]}  created={ver.created_at}")
        print("=" * 78)

        rows = TE.objects.filter(timetable_version=ver).select_related(
            "period", "instructional_group", "lesson_requirement__subject"
        )

        by_class_day = defaultdict(list)
        for e in rows:
            lr = e.lesson_requirement
            subj = getattr(lr, "subject", None) if lr else None
            code = (subj.code if subj else "") or ""
            code = code.upper()
            if not code:
                continue
            ig = e.instructional_group.name if e.instructional_group else "?"
            pnum = getattr(e.period, "number", None) if e.period else None
            if pnum is None:
                continue
            day = str(e.day or "").upper()
            by_class_day[(ig, day)].append((pnum, code))

        adjacency_violations = []
        adjacency_practical = []  # informational only
        maths_afternoon = []
        maths_morning = 0

        for (ig, day), items in sorted(by_class_day.items()):
            items.sort(key=lambda x: x[0])
            for i in range(len(items) - 1):
                p1, c1 = items[i]
                p2, c2 = items[i + 1]
                if p2 != p1 + 1:
                    continue
                # practicals → informational
                if c1 in PRACTICAL or c2 in PRACTICAL:
                    if c1 in COMPLEX or c2 in COMPLEX:
                        adjacency_practical.append((ig, day, p1, c1, p2, c2))
                    continue
                if c1 not in COMPLEX or c2 not in COMPLEX:
                    continue
                if c1 == c2:
                    continue  # same-subject double lesson allowed
                adjacency_violations.append((ig, day, p1, c1, p2, c2))

            for p, c in items:
                if c in MATHS:
                    if p > MATHS_MORNING_CUTOFF:
                        maths_afternoon.append((ig, day, p, c))
                    else:
                        maths_morning += 1

        print(f"Complex-subject adjacency violations: {len(adjacency_violations)}")
        for ig, day, p1, c1, p2, c2 in adjacency_violations[:30]:
            print(f"  {ig:44} {day}  P{p1} {c1:8} \u2192 P{p2} {c2}")

        print()
        print(f"Maths placements before P{MATHS_MORNING_CUTOFF + 1}: {maths_morning}")
        print(f"Maths placements at  P{MATHS_MORNING_CUTOFF + 1}+: {len(maths_afternoon)}")
        for ig, day, p, c in maths_afternoon[:30]:
            print(f"  {ig:44} {day}  P{p} {c}")

        print()
        print(f"Practicals adjacent to a complex subject (excluded, informational): "
              f"{len(adjacency_practical)}")
        for ig, day, p1, c1, p2, c2 in adjacency_practical[:10]:
            print(f"  {ig:44} {day}  P{p1} {c1:8} \u2192 P{p2} {c2}")

        total_bad = len(adjacency_violations) + len(maths_afternoon)
        status = "PASS" if not adjacency_violations and not maths_afternoon else "REVIEW"
        print()
        print(f"RESULT: adjacency={len(adjacency_violations)} "
              f"maths_afternoon={len(maths_afternoon)} "
              f"| total_bad={total_bad} | {status}")
        print()
