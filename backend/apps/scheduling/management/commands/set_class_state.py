from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Deactivate a class (IG + its LessonRequirements) or reactivate with --reactivate"
    def add_arguments(self, p):
        p.add_argument("keys", nargs="+", help="IG name or code, e.g. Grade 8E or 8E or G8E")
        p.add_argument("--reactivate", action="store_true")
        p.add_argument("--commit", action="store_true")
        p.add_argument("--list", action="store_true", help="Just list all IGs and exit")

    def resolve(self, IG, key):
        # try exact name
        g = IG.objects.filter(name=key).first()
        if g: return g
        # try exact code
        g = IG.objects.filter(code=key).first()
        if g: return g
        # try normalised: strip "Grade ", "G", spaces; compare to code
        norm = key.replace("Grade", "").replace("G", "").replace(" ", "").strip()
        for cand in IG.objects.all():
            if cand.code.replace(" ", "") == norm or cand.name.replace("Grade", "").replace(" ", "") == norm:
                return cand
        return None

    def handle(self, *a, **kw):
        IG = M("InstructionalGroup"); LR = M("LessonRequirement")

        if kw["list"]:
            print(f"{'Name':14s} {'Code':6s} {'Active':7s} LRs")
            print("-" * 40)
            for g in IG.objects.all().order_by("name"):
                n = LR.objects.filter(instructional_group=g).count()
                print(f"{g.name:14s} {g.code:6s} {str(g.is_active):7s} {n}")
            return

        target_state = kw["reactivate"]
        plan = []
        for key in kw["keys"]:
            g = self.resolve(IG, key)
            if not g:
                print(f"  {key}: NOT FOUND"); continue
            lrs = LR.objects.filter(instructional_group=g)
            total = lrs.count()
            to_change = lrs.filter(is_active=not target_state).count()
            plan.append((g, total))
            print(f"  {g.name:14s} (code={g.code}) IG.active={str(g.is_active):5s} "
                  f"LRs total={total:3d} to_change={to_change:3d}")

        if not kw["commit"]:
            verb = "active" if target_state else "inactive"
            print(f"\nDRY RUN — would set {verb} on the above. Pass --commit to apply.")
            return

        with transaction.atomic():
            for g, total in plan:
                g.is_active = target_state
                g.save()
                LR.objects.filter(instructional_group=g).update(is_active=target_state)
                print(f"  {g.name}: IG + {total} LRs -> is_active={target_state}")
