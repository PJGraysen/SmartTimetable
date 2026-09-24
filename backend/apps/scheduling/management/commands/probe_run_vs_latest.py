from django.core.management.base import BaseCommand
from django.apps import apps as _reg
from rest_framework.renderers import JSONRenderer

def M(n):
    for m in _reg.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    def handle(self, *a, **kw):
        SR = M('SchedulingRun'); TV = M('TimetableVersion'); TE = M('TimetableEntry')
        # latest completed run
        run = SR.objects.filter(status='COMPLETED').order_by('-created_at').first() or SR.objects.order_by('-created_at').first()
        print('Latest SchedulingRun:', run.pk if run else None, 'status=', getattr(run,'status',None), 'version_fk=', getattr(run,'timetable_version_id',None))
        tv = getattr(run, 'timetable_version', None) or TV.objects.order_by('-version_number').first()
        print('Run.pointed version:', tv.pk, tv.version_number, tv.name)
        latest_tv = TV.objects.order_by('-version_number').first()
        print('Latest TV in DB   :', latest_tv.pk, latest_tv.version_number, latest_tv.name)
        print('MATCH:', tv.pk == latest_tv.pk)
        # form 4 subject loads from the version the API is serving
        for label, version in (('run-version', tv), ('latest-DB', latest_tv)):
            print()
            print('---- ', label, version.version_number, version.name, ' ----')
            for ig in ('Form 4E','Form 4W'):
                c = {}
                for e in TE.objects.filter(timetable_version=version, instructional_group__name=ig).select_related('lesson_requirement__subject'):
                    sub = e.lesson_requirement.subject.code if (e.lesson_requirement and e.lesson_requirement.subject) else '?'
                    c[sub] = c.get(sub, 0) + 1
                print('   ', ig, c)
