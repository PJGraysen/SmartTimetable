from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    def handle(self, *a, **kw):
        Subject = M("Subject"); LR = M("LessonRequirement")
        gst = Subject.objects.filter(code="GST").first()
        if not gst:
            print("GST subject not in DB"); return
        n = LR.objects.filter(subject=gst).count()
        print(f"Deleting {n} GST LessonRequirement rows…")
        LR.objects.filter(subject=gst).delete()
        print("Done. Subject GST left in place (harmless).")
