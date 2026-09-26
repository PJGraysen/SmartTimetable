from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Create Grade 11 TeachingGroup + InstructionalGroup by cloning Grade 10"
    def add_arguments(self, p):
        p.add_argument("--commit", action="store_true")

    def handle(self, *a, **kw):
        TG = M("TeachingGroup"); IG = M("InstructionalGroup")

        pairs = [("Grade 10E", "Grade 11E", "11E"),
                 ("Grade 10W", "Grade 11W", "11W")]

        plan = []
        for src_name, dst_name, dst_code in pairs:
            src_ig = IG.objects.filter(name=src_name).first()
            if not src_ig:
                print(f"SKIP: {src_name} IG not found"); continue
            src_tg = src_ig.teaching_group
            plan.append((src_ig, src_tg, dst_name, dst_code))

        print(f"{'Source':12s} -> {'Target':12s}  code  learners  stream(from src TG)")
        print("-" * 70)
        for src_ig, src_tg, dst_name, dst_code in plan:
            print(f"{src_ig.name:12s} -> {dst_name:12s}  {dst_code:4s}  "
                  f"{src_ig.learner_count:3d}      {src_tg.stream}")

        existing = [n for _,_,n,_ in plan if IG.objects.filter(name=n).exists()]
        if existing:
            print(f"\nAlready exist (will update): {existing}")

        if not kw["commit"]:
            print("\nDRY RUN — pass --commit to write")
            return

        with transaction.atomic():
            for src_ig, src_tg, dst_name, dst_code in plan:
                # TeachingGroup
                tg, tg_new = TG.objects.get_or_create(
                    name=dst_name,
                    defaults={
                        "stream": src_tg.stream,
                        "code": dst_code,
                        "learner_count": src_ig.learner_count,
                        "is_active": True,
                    },
                )
                # InstructionalGroup
                ig, ig_new = IG.objects.get_or_create(
                    name=dst_name,
                    defaults={
                        "teaching_group": tg,
                        "code": dst_code,
                        "learner_count": src_ig.learner_count,
                        "is_active": True,
                    },
                )
                print(f"  {dst_name}: TG {'created' if tg_new else 'exists'} | "
                      f"IG {'created' if ig_new else 'exists'}")
