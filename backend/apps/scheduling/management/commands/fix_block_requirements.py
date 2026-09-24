from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Fix the over-declared BLOCK/parallel requirements"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        LR = M("LessonRequirement")
        IG = M("InstructionalGroup")
        SUBJ = M("Subject")
        apply = kw["apply"]
        print("APPLY:", apply)
        print()

        # ---- One subject per parallel block, per form ----
        # Form 4E: GEO (from GEO_HIS), AGR (from AGR_BST)
        # Form 4W: HIS (from GEO_HIS), BUS (from AGR_BST)
        # Grade 10E: COMP, BIO, MUSD, BUS   (one per option block)
        # Grade 10W: CHEM, GEO, PHY, AGR
        PLAN = {
            "Form 4E":  {"keep": ["GEO","AGR"], "drop": ["HIS","BUS"]},
            "Form 4W":  {"keep": ["HIS","BUS"], "drop": ["GEO","AGR"]},
            "Grade 10E":{"keep": ["COMP","GEO","MUSD","BUS"], "drop": ["CHEM","BIO","HIS","PHY","LIT","AGR"]},
            "Grade 10W":{"keep": ["CHEM","BIO","PHY","AGR"], "drop": ["COMP","GEO","HIS","LIT","MUSD","BUS"]},
        }

        for group_name, plan in PLAN.items():
            ig = IG.objects.filter(name=group_name).first()
            if not ig:
                print(f"!! {group_name} not found"); continue
            print(f"== {group_name} ==")
            for subj_code in plan["drop"]:
                subj = SUBJ.objects.filter(code=subj_code).first()
                if not subj: continue
                qs = LR.objects.filter(instructional_group=ig, subject=subj, is_active=True)
                n = qs.count()
                if n == 0:
                    print(f"   (no rows to drop for {subj_code})")
                    continue
                for r in qs:
                    print(f"   DROP {subj_code} n={r.lessons_per_week} req={r.id}")
                    if apply:
                        r.is_active = False
                        r.save(update_fields=["is_active"])
            total_keep = 0
            for subj_code in plan["keep"]:
                subj = SUBJ.objects.filter(code=subj_code).first()
                if not subj: continue
                for r in LR.objects.filter(instructional_group=ig, subject=subj, is_active=True):
                    total_keep += r.lessons_per_week
            print(f"   BLOCK lessons kept: {total_keep}")
        print()
        print("Dry run complete. Re-run with --apply to persist." if not apply else "Applied.")
