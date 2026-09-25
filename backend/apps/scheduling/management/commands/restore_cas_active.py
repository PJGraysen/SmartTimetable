from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    def handle(self, *a, **kw):
        Subject = M("Subject"); LR = M("LessonRequirement")
        cas = Subject.objects.filter(code="CAS").first()
        for r in LR.objects.filter(subject=cas):
            if not r.is_active:
                r.is_active = True
                r.save(update_fields=["is_active"])
                print(f"  reactivated CAS on {r.instructional_group.name}")
        print("done")
