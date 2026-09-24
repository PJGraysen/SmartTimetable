from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

class Command(BaseCommand):
    def handle(self, *a, **kw):
        LR = M('LessonRequirement')
        print('TOTAL rows:', LR.objects.count(), ' active:', LR.objects.filter(is_active=True).count())
        print()
        cur = None; counts = {}
        for r in LR.objects.filter(is_active=True).select_related('instructional_group','subject','teacher').order_by('instructional_group__name','subject__code','requirement_type'):
            ig = r.instructional_group.name
            sub = r.subject.code if r.subject else '?'
            rt = r.requirement_type or '-'
            t = str(r.teacher) if r.teacher else '-'
            if ig != cur:
                if cur:
                    print(f'  >> SUM for {cur}: {sum(counts.values())}')
                print()
                print(f'== {ig} ==')
                cur = ig; counts = {}
            print(f'   {sub:6s} {str(rt):22s} n={r.lessons_per_week:3d}  teacher={t}')
            counts[sub] = counts.get(sub, 0) + r.lessons_per_week
        if cur:
            print(f'  >> SUM for {cur}: {sum(counts.values())}')
