from django.core.management.base import BaseCommand
from django.apps import apps
from collections import Counter

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Reproduce the diversity constraint and check for duplicate vars"
    def handle(self, *a, **kw):
        from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
        from apps.scheduling.engine.solver.model import SolverModelBuilder
        from apps.scheduling.engine.solver.objective import (
            BalancedTeacherWorkloadObjective,
            CompositeSolverObjective,
            TeacherConsecutivePeriodObjective,
        )
        from collections import defaultdict

        Term = M("Term")
        TV = M("TimetableVersion")
        TE = M("TimetableEntry")

        term = Term.objects.filter(is_active=True).first() or Term.objects.first()
        problem = DjangoSchedulingLoader().load_problem(term=term)

        objective = CompositeSolverObjective(objectives=(
            BalancedTeacherWorkloadObjective(),
            TeacherConsecutivePeriodObjective(),
        ))
        builder = SolverModelBuilder(objective=objective)
        solver_model = builder.build(problem)

        # REPLICATE the diversity constraint
        prev = TV.objects.order_by("-version_number").first()
        print(f"Previous version: v{prev.version_number}")

        prev_map = {}
        for e in TE.objects.filter(timetable_version=prev).only(
            "instructional_group_id","day","period_id","lesson_requirement_id"
        ):
            prev_map[(str(e.instructional_group_id), str(e.day or "").upper(),
                      str(e.period_id))] = str(e.lesson_requirement_id)

        print(f"prev_map entries: {len(prev_map)}")

        prev_per_class = defaultdict(int)
        for (ig, d, p) in prev_map:
            prev_per_class[ig] += 1

        same_vars_per_class = defaultdict(list)
        for v in solver_model.variables:
            k = (str(v.instructional_group_id), str(v.day or "").upper(), str(v.period_id))
            if prev_map.get(k) == str(v.lesson_requirement_id):
                same_vars_per_class[k[0]].append(v.variable)

        print()
        print("Per-class duplicate analysis:")
        for ig, vs in same_vars_per_class.items():
            # Check for duplicates: the same variable object twice
            seen = Counter()
            for v in vs:
                seen[id(v)] += 1
            dups = {k: c for k, c in seen.items() if c > 1}
            print(f"  {ig[:8]}  variables={len(vs)}  unique_ids={len(seen)}  duplicate_entries={sum(c-1 for c in dups.values())}")

        # Try adding and see if it crashes
        print()
        print("Attempting to apply the diversity constraint...")
        try:
            for ig, vs in same_vars_per_class.items():
                n = prev_per_class.get(ig, 0)
                if n == 0: continue
                limit = max(1, int(0.15 * n))
                solver_model.model.add(sum(vs) <= limit)
            print("  Constraint added OK (no crash yet)")
        except Exception as e:
            print(f"  EXCEPTION: {type(e).__name__}: {e}")

        # Now validate
        print()
        print("Calling model.validate()...")
        try:
            errs = solver_model.model.validate()
            if errs:
                print(f"  validate() returned {len(errs)} errors:")
                for e in errs[:10]:
                    print(f"    {e}")
            else:
                print("  validate() returned EMPTY")
        except Exception as e:
            print(f"  validate() raised: {type(e).__name__}: {e}")
