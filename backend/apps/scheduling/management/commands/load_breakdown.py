from django.core.management.base import BaseCommand
from django.apps import apps
from collections import defaultdict

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Per-teacher load broken down by instructional group (Grade 8 contribution visible)"
    def handle(self, *a, **kw):
        LR = M("LessonRequirement"); IG = M("InstructionalGroup")
        Teacher = M("Teacher")

        active_lr = LR.objects.filter(is_active=True).select_related(
            "teacher", "instructional_group", "subject"
        )

        by_tg = defaultdict(lambda: defaultdict(int))
        subs_tg = defaultdict(lambda: defaultdict(set))

        for r in active_lr:
            if not r.teacher_id or not r.instructional_group_id:
                continue
            g = r.instructional_group.name
            by_tg[r.teacher_id][g] += r.lessons_per_week
            if r.subject:
                subs_tg[r.teacher_id][g].add(r.subject.code)

        def gkey(name):
            for i, pref in enumerate((
                "Grade 8", "Grade 9", "Grade 10", "Grade 11",
                "Form 1", "Form 2", "Form 3", "Form 4"
            )):
                if name.startswith(pref):
                    return (i, name)
            return (99, name)

        print(f"{'Code':6s} {'Name':28s} {'Total':>5s}  Breakdown")
        print("-" * 100)

        grand = 0
        g8_total = defaultdict(int)
        for t in Teacher.objects.filter(is_active=True).order_by("employee_code"):
            groups = by_tg.get(t.pk, {})
            total = sum(groups.values())
            grand += total
            if not groups:
                print(f"{t.employee_code:6s} {str(t)[:28]:28s} {total:5d}  (no load)")
                continue
            marker = "  <<< OVER" if total > 46 else ("  (near cap)" if total >= 42 else "")
            print(f"{t.employee_code:6s} {str(t)[:28]:28s} {total:5d}{marker}")
            for g in sorted(groups, key=gkey):
                subs = ",".join(sorted(subs_tg[t.pk][g]))
                print(f"{'':6s} {'':28s} {'':5s}    {g} = {groups[g]:2d}  [{subs}]")
                if g.startswith("Grade 8"):
                    g8_total[t.pk] += groups[g]

        print("-" * 100)
        print(f"Grand total active lessons: {grand}")

        print()
        print("=== Grade 8 contribution (freed when Grade 8 is deactivated) ===")
        print(f"{'Code':6s} {'Name':28s} {'G8':>4s}  {'Now':>4s} -> {'After':>5s}")
        print("-" * 60)
        for t in Teacher.objects.filter(is_active=True).order_by("employee_code"):
            g8 = g8_total.get(t.pk, 0)
            if not g8:
                continue
            total = sum(by_tg.get(t.pk, {}).values())
            after = total - g8
            flag = "  ✅" if after <= 46 else "  ❌ still over"
            print(f"{t.employee_code:6s} {str(t)[:28]:28s} {g8:4d}  {total:4d} -> {after:5d}{flag}")
