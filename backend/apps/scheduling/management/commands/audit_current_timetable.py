from django.core.management.base import BaseCommand
from django.apps import apps as _reg
from collections import Counter

def M(name):
    for m in _reg.get_models():
        if m.__name__ == name: return m
    raise LookupError(name)

class Command(BaseCommand):
    help = 'Diagnose Form 4 swap and day format'
    def handle(self, *a, **kw):
        TV = M('TimetableVersion'); TE = M('TimetableEntry'); LR = M('LessonRequirement')
        latest = TV.objects.order_by('-version_number').first()
        print('Latest:', latest.pk, latest.version_number, latest.name)

        days = list(TE.objects.filter(timetable_version=latest).values_list('day', flat=True).distinct())
        print('DISTINCT day values:', days)
        pers = list(TE.objects.filter(timetable_version=latest).values_list('period__name', flat=True).distinct())
        print('DISTINCT period names:', pers)

        print()
        print('=== Form 4 LessonRequirements in DB ===')
        for r in LR.objects.filter(instructional_group__name__startswith='Form 4').select_related('instructional_group','subject','teacher'):
            print('  IG=', r.instructional_group.name, ' subj=', r.subject.code if r.subject else None, ' need=', r.lessons_per_week, ' teacher=', r.teacher)

        print()
        print('=== Form 4 Entries: entry.IG vs req.IG ===')
        rows = []
        for e in TE.objects.filter(timetable_version=latest, instructional_group__name__startswith='Form 4').select_related('instructional_group','lesson_requirement__instructional_group','lesson_requirement__subject','period'):
            e_ig = e.instructional_group.name if e.instructional_group else None
            r_ig = e.lesson_requirement.instructional_group.name if (e.lesson_requirement and e.lesson_requirement.instructional_group) else None
            subj = e.lesson_requirement.subject.code if (e.lesson_requirement and e.lesson_requirement.subject) else None
            rows.append((e.day, e.period.name if e.period else None, e_ig, r_ig, subj))
        mismatch = [r for r in rows if r[2] != r[3]]
        print('Form 4 entries total:', len(rows), ' entry.IG != req.IG:', len(mismatch))
        shown = 0
        for r in mismatch:
            print('   day=', r[0], 'period=', r[1], 'entry.IG=', r[2], 'req.IG=', r[3], 'subj=', r[4])
            shown += 1
            if shown >= 30: break

        print()
        print('=== subject placement per Form 4 group, grouped by entry.IG ===')
        for ig_name in ('Form 4E','Form 4W'):
            c = Counter()
            for e in TE.objects.filter(timetable_version=latest, instructional_group__name=ig_name).select_related('lesson_requirement__subject'):
                if e.lesson_requirement and e.lesson_requirement.subject:
                    c[e.lesson_requirement.subject.code] += 1
            print(' ', ig_name, dict(c))

        print('=== DONE ===')
