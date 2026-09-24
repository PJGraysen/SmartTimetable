from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    def handle(self, *a, **kw):
        Subject = M("Subject"); LR = M("LessonRequirement")
        cas = Subject.objects.filter(code="CAS").first()
        if not cas:
            print("no CAS subject"); return
        n = 0
        for r in LR.objects.filter(subject=cas, is_active=True):
            r.is_active = False
            r.save(update_fields=["is_active"])
            print(f"  deactivated CAS on {r.instructional_group.name}")
            n += 1
        print(f"Deactivated {n} CAS LR(s)")
