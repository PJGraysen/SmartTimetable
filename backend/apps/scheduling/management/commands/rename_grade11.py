from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Rename Grade 11E/11W IG and TG name to G11E/G11W (code unchanged)"
    def add_arguments(self, p):
        p.add_argument("--commit", action="store_true")
    def handle(self, *a, **kw):
        IG = M("InstructionalGroup"); TG = M("TeachingGroup")
        renames = [("Grade 11E", "G11E"), ("Grade 11W", "G11W")]
        plan = []
        for old, new in renames:
            ig = IG.objects.filter(name=old).first()
            if not ig:
                print(f"  {old}: IG not found, skipping"); continue
            tg = ig.teaching_group
            print(f"  IG  name={ig.name!r:16s} code={ig.code!r:6s} -> name={new!r}")
            if tg:
                print(f"  TG  name={tg.name!r:16s} code={tg.code!r:6s} -> name={new!r}")
            plan.append((ig, tg, new))
        if not kw["commit"]:
            print("\nDRY RUN — pass --commit to write")
            return
        with transaction.atomic():
            for ig, tg, new in plan:
                ig.name = new; ig.save(update_fields=["name"])
                if tg:
                    tg.name = new; tg.save(update_fields=["name"])
                print(f"  renamed -> {new}")
