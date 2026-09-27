from django.core.management.base import BaseCommand
from apps.scheduling.engine.solver import model as M
import inspect

class Command(BaseCommand):
    help = "Trace block resolution: which map for which group"
    def handle(self, *a, **kw):
        for name in (
            "_senior_school_group_block_code",
            "_normalized_group_code",
            "_senior_school_block_for_subject",
            "resolve_senior_school_block",
        ):
            fn = getattr(M, name, None)
            if fn is None:
                continue
            print(f"=== {name} ===")
            try:
                print(inspect.getsource(fn))
            except Exception as e:
                print(f"  (no source: {e})")
            print()

        print("=== GRADE10_PARALLEL_SUBJECT_TO_BLOCK ===")
        print(f"  {M.GRADE10_PARALLEL_SUBJECT_TO_BLOCK}")
        print()
        print("=== SENIOR_SCHOOL_SUBJECT_TO_BLOCK ===")
        s = getattr(M, "SENIOR_SCHOOL_SUBJECT_TO_BLOCK", None)
        print(f"  {s}")
        print()
        print("=== Live resolution: group + subject -> block ===")
        IG = None
        for m in __import__("django.apps", fromlist=["apps"]).apps.get_models():
            if m.__name__ == "InstructionalGroup":
                IG = m; break

        resolver = getattr(M, "_senior_school_group_block_code", None)
        if not resolver:
            print("  resolver not found — inspect above sources manually")
            return

        tests = [
            ("Grade 10E", "COMP"), ("Grade 10E", "CHEM"),
            ("Grade 10E", "BUS"),  ("Grade 10E", "AGR"),
            ("Grade 10E", "MUSD"), ("Grade 10E", "PHY"),
            ("Grade 10E", "ICT"),  ("Grade 10E", "ENG"),
            ("Grade 11E", "COMP"), ("Grade 11E", "BUS"),
            ("Grade 11E", "ICT"),  ("Grade 11E", "ENG"),
            ("Form 3E",  "GEO"),   ("Form 3E",  "AGR"),
        ]
        for gname, subj in tests:
            g = IG.objects.filter(name=gname).first()
            if not g:
                print(f"  {gname:10s} {subj:6s} -> (group not found)")
                continue
            try:
                code = resolver(g, subj)
            except Exception as e:
                code = f"ERR {e}"
            print(f"  {gname:10s} {subj:6s} -> {code}")
