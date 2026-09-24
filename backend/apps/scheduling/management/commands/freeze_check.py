from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    help = "Compare last N versions cell-by-cell per class (freeze check)"
    def add_arguments(self, p):
        p.add_argument("--versions", type=int, default=4)
    def handle(self, *a, **kw):
        TV = M("TimetableVersion"); TE = M("TimetableEntry")
        n = kw["versions"]

        vs = list(TV.objects.order_by("-version_number")[:n])
        if len(vs) < 2:
            print(f"Need at least 2 versions, found {len(vs)}")
            return

        print(f"Comparing last {len(vs)} versions:")
        for v in vs:
            print(f"  v{v.version_number} (id={str(v.pk)[:8]}) {v.name} created={v.created_at}")
        print()

        def snapshot(v):
            out = {}
            for e in TE.objects.filter(timetable_version=v).only(
                "instructional_group_id","day","period_id","lesson_requirement_id"
            ):
                out[(str(e.instructional_group_id), e.day, str(e.period_id))] = str(e.lesson_requirement_id)
            return out

        snaps = [(v.version_number, snapshot(v)) for v in vs]

        # Per-class breakdown between the two newest
        newest_n, newest = snaps[0]
        prev_n, prev = snaps[1]

        from collections import defaultdict
        per_class_new = defaultdict(dict)
        per_class_prev = defaultdict(dict)
        for (ig, d, p), lr in newest.items(): per_class_new[ig][(d,p)] = lr
        for (ig, d, p), lr in prev.items():   per_class_prev[ig][(d,p)] = lr

        # Map ig-id to name
        IG = M("InstructionalGroup")
        names = {str(g.pk): g.name for g in IG.objects.all()}

        print(f"=== FREEZE CHECK: v{newest_n} vs v{prev_n} ===")
        print(f"{'CLASS':14s} {'PREV':>5s} {'NEW':>5s} {'SAME':>5s} {'CHANGED':>8s} {'%CHANGED':>9s}")
        print("-" * 62)
        for ig in sorted(set(per_class_new) | set(per_class_prev)):
            name = names.get(ig, ig[:8])
            prev_cells = per_class_prev.get(ig, {})
            new_cells = per_class_new.get(ig, {})
            common = set(prev_cells) & set(new_cells)
            same = sum(1 for k in common if prev_cells[k] == new_cells[k])
            total = max(len(prev_cells), len(new_cells), 1)
            changed = total - same
            pct = 100.0 * changed / total
            print(f"{name:14s} {len(prev_cells):>5d} {len(new_cells):>5d} {same:>5d} {changed:>8d} {pct:>8.1f}%")
        print()

        # Also show all adjacent pairs
        if len(snaps) > 2:
            print("=== ALL ADJACENT PAIRS ===")
            for i in range(len(snaps)-1):
                a_n, a = snaps[i]
                b_n, b = snaps[i+1]
                common = set(a) & set(b)
                same = sum(1 for k in common if a[k] == b[k])
                total = len(common) or 1
                pct = 100.0 * (total - same) / total
                print(f"  v{b_n} -> v{a_n}: {total-same}/{total} changed = {pct:.1f}%  (identical={same})")
