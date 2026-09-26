from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Inspect TeachingGroup + Grade 10 group wiring"
    def handle(self, *a, **kw):
        TG = M("TeachingGroup"); IG = M("InstructionalGroup")

        print("=== TeachingGroup fields ===")
        for f in TG._meta.get_fields():
            if hasattr(f, "column"):
                null = "NULL" if getattr(f, "null", False) else "NOT NULL"
                blank = "blank" if getattr(f, "blank", False) else ""
                print(f"  {f.name:30s} {type(f).__name__:20s} {null} {blank}")

        print()
        print("=== TeachingGroup rows ===")
        for t in TG.objects.all().order_by("name"):
            print(f"  {str(t.pk)[:8]}  {t.name}")

        print()
        print("=== Grade 10E / 10W wiring ===")
        for name in ("Grade 10E", "Grade 10W", "Grade 8E", "Form 3E"):
            g = IG.objects.filter(name=name).first()
            if not g:
                print(f"  {name}: NOT FOUND"); continue
            tg = getattr(g, "teaching_group", None)
            print(f"  {name:12s} code={g.code!r:10s} learners={g.learner_count:3d} "
                  f"active={g.is_active} teaching_group={tg.name if tg else None}")

        print()
        print("=== Form 3 active LessonRequirements ===")
        LR = M("LessonRequirement")
        for name in ("Form 3E", "Form 3W"):
            g = IG.objects.filter(name=name).first()
            if not g: continue
            qs = LR.objects.filter(instructional_group=g)
            print(f"  {name}: total={qs.count()} active={qs.filter(is_active=True).count()}")
