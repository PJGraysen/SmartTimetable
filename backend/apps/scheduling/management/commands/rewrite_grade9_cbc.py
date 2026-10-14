from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

# CBC Grade 9 curriculum mirrors Grade 8 per DOCX contract
TARGET = {
    "MAT": 5, "ENG": 5, "KIS": 5, "SOCIAL": 5, "INTSCI": 5,
    "AGR": 5, "CAS": 5, "CRE": 3, "PPI": 1,
}
DROP = {"BIO","CHEM","COMP","GEO","PHY"}  # 8-4-4 subjects not used in CBC

class Command(BaseCommand):
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
        p.add_argument(
            "--term", dest="term_name", default=None,
            help="Term name (e.g. 'Term 3'). Defaults to active term.",
        )
    def handle(self, *a, **kw):
        LR = M("LessonRequirement"); IG = M("InstructionalGroup"); SUBJ = M("Subject")
        Term = M("Term")
        term_name = kw.get("term_name")
        if term_name:
            term = Term.objects.filter(
                name__iexact=term_name.strip()
            ).first()
            if not term:
                avail = list(Term.objects.values_list("name", flat=True).order_by("name"))
                raise SystemExit(
                    f"Term {term_name!r} not found. Available: {avail}"
                )
        else:
            term = (
                Term.objects.filter(is_active=True).first()
                or Term.objects.first()
            )
        print(f"Target term: {term.name if term else '<none>'}")
        apply = kw["apply"]

        for gname in ("Grade 9E","Grade 9W"):
            ig = IG.objects.filter(name=gname).first()
            if not ig:
                print(f"{gname} missing"); continue
            print(f"== {gname} ==")
            # 1. deactivate 8-4-4 subjects
            for code in DROP:
                subj = SUBJ.objects.filter(code=code).first()
                if not subj: continue
                for r in LR.objects.filter(term=term, instructional_group=ig, subject=subj, is_active=True):
                    print(f"   DEACT {code} n={r.lessons_per_week}")
                    if apply:
                        r.is_active = False
                        r.save(update_fields=["is_active"])
            # 2. ensure CBC subjects exist
            for code, n in TARGET.items():
                subj = SUBJ.objects.filter(code=code).first()
                if not subj:
                    print(f"   !! subject {code} missing from Subject table")
                    continue
                r = LR.objects.filter(term=term, instructional_group=ig, subject=subj).first()
                if r and r.is_active and r.lessons_per_week == n:
                    print(f"   OK   {code} n={n}")
                    continue
                if r:
                    print(f"   UPDATE {code} n={r.lessons_per_week} -> {n}")
                    if apply:
                        r.lessons_per_week = n
                        r.is_active = True
                        r.save(update_fields=["lessons_per_week","is_active"])
                else:
                    print(f"   ADD  {code} n={n}")
                    if apply:
                        LR.objects.create(
                            instructional_group=ig, subject=subj, term=term,
                            lessons_per_week=n, requirement_type="STANDALONE",
                            is_active=True,
                        )
        print()
        print("Applied." if apply else "Dry run — add --apply.")
