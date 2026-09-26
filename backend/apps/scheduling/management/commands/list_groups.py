from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "List IG names and codes to verify G11 rename"
    def handle(self, *a, **kw):
        IG = M("InstructionalGroup")
        for g in IG.objects.all().order_by("name"):
            print(f"  {g.name:16s} code={g.code:6s} active={g.is_active}")
