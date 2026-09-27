"""Compare the last N persisted timetable versions cell-by-cell."""
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.apps import apps


def M(n):
    for m in apps.get_models():
        if m.__name__ == n:
            return m


class Command(BaseCommand):
    help = "Compare the last N persisted timetable versions and report % change."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=3,
                            help="How many of the latest versions to compare.")

    def handle(self, *args, **opts):
        TV = M("TimetableVersion")
        n = opts["count"]
        versions = list(TV.objects.order_by("-version_number")[:n])
        if len(versions) < 2:
            self.stdout.write("Need at least 2 versions to compare.")
            return

        versions = list(reversed(versions))  # oldest first
        self.stdout.write("=== Versions being compared (oldest → newest) ===")
        for v in versions:
            entries = v.entries.count()
            self.stdout.write(
                f"  v{v.version_number}  id={str(v.pk)[:8]}  entries={entries}"
                f"  name={getattr(v, 'name', '?')}"
            )
        self.stdout.write("")

        def cell_map(version):
            """Return dict[(day, period_id, ig_id)] = sorted tuple of 'SUBJ/TCH/ROOM' strings."""
            m = defaultdict(list)
            qs = version.entries.select_related(
                "instructional_group", "lesson_requirement__subject",
                "teacher", "room",
            )
            for e in qs:
                ig = getattr(e.instructional_group, "name", "?")
                subj = getattr(getattr(e.lesson_requirement, "subject", None), "code", "?")
                tch = getattr(e.teacher, "employee_code", None) or "-"
                rm = getattr(e.room, "code", None) or "-"
                key = (e.day, str(e.period_id), str(e.instructional_group_id))
                m[key].append(f"{subj}|{tch}|{rm}")
            for k in m:
                m[k] = tuple(sorted(m[k]))
            return m

        maps = [(v, cell_map(v)) for v in versions]

        # Pairwise comparison of consecutive versions
        self.stdout.write("=== Pairwise comparisons (consecutive) ===")
        for i in range(1, len(maps)):
            vA, mA = maps[i-1]
            vB, mB = maps[i]
            self._compare(vA, mA, vB, mB)

        # All-versions intersection / union
        self.stdout.write("\n=== Overall: are all 3 identical? ===")
        keys_A = set(maps[0][1].keys())
        keys_B = set(maps[1][1].keys())
        keys_C = set(maps[2][1].keys()) if len(maps) >= 3 else set()
        all_keys = keys_A | keys_B | keys_C

        same_AB = sum(1 for k in all_keys
                       if maps[0][1].get(k) == maps[1][1].get(k))
        same_BC = sum(1 for k in all_keys
                       if len(maps) >= 3 and maps[1][1].get(k) == maps[2][1].get(k))
        same_all = sum(1 for k in all_keys
                        if len(maps) >= 3
                        and maps[0][1].get(k) == maps[1][1].get(k) == maps[2][1].get(k))
        self.stdout.write(f"  Total distinct cells across all versions: {len(all_keys)}")
        self.stdout.write(f"  Cells identical in oldest↔middle:  {same_AB}")
        if len(maps) >= 3:
            self.stdout.write(f"  Cells identical in middle↔newest:  {same_BC}")
            self.stdout.write(f"  Cells identical in all 3:          {same_all}")

    def _compare(self, vA, mA, vB, mB):
        self.stdout.write(
            f"\n--- v{vA.version_number} → v{vB.version_number} ---"
        )
        all_keys = set(mA.keys()) | set(mB.keys())
        changed = 0
        by_day = defaultdict(int)
        samples = []
        for k in sorted(all_keys):
            a = mA.get(k, ())
            b = mB.get(k, ())
            if a != b:
                changed += 1
                by_day[k[0]] += 1
                if len(samples) < 8:
                    samples.append((k, a, b))

        total = len(all_keys) or 1
        pct = 100.0 * changed / total
        self.stdout.write(f"  cells compared:   {total}")
        self.stdout.write(f"  cells changed:    {changed}  ({pct:.1f}%)")
        self.stdout.write(f"  cells unchanged:  {total - changed}")
        self.stdout.write(f"  by day: " + ", ".join(
            f"{d}={n}" for d, n in sorted(by_day.items())
        ) or "  by day: none")

        if samples:
            self.stdout.write("  sample differences (first 8):")
            for (day, pid, igid), a, b in samples:
                short = str(igid)[:8]
                self.stdout.write(f"    {day} period={str(pid)[:8]} ig={short}")
                self.stdout.write(f"      A: {a if a else '(empty)'}")
                self.stdout.write(f"      B: {b if b else '(empty)'}")

        # Per-group diff count
        by_group = defaultdict(lambda: [0, 0])  # [changed, total]
        for k in all_keys:
            ig = k[2]
            by_group[ig][1] += 1
            if mA.get(k, ()) != mB.get(k, ()):
                by_group[ig][0] += 1

        # Resolve group names
        IG = M("InstructionalGroup")
        names = dict(IG.objects.values_list("id", "name"))
        self.stdout.write("  per-group changed/total:")
        for ig, (c, t) in sorted(by_group.items(), key=lambda x: str(x[0])):
            name = names.get(ig) or str(ig)[:8]
            pct_g = 100.0 * c / t if t else 0
            self.stdout.write(f"    {name:12s} {c:3d}/{t:3d}  ({pct_g:.0f}%)")
