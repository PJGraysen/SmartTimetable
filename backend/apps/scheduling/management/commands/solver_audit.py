import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Find solver handling of BLOCK/shared electives"
    def handle(self, *a, **kw):
        from apps.academics import __file__ as ac
        apps_dir = os.path.dirname(os.path.dirname(ac))
        print(f"Apps dir: {apps_dir}\n")

        kws = ("requirement_type", "BLOCK", "STANDALONE", "is_block",
               "shared", "simultaneous", "elective")
        hits_by_file = {}

        for root, dirs, files in os.walk(apps_dir):
            dirs[:] = [d for d in dirs if d not in ("migrations", "__pycache__", "tests")]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                path = os.path.join(root, fname)
                rel = os.path.relpath(path, apps_dir)
                with open(path, encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, 1):
                        for kw in kws:
                            if kw in line:
                                hits_by_file.setdefault(rel, []).append(
                                    (lineno, kw, line.rstrip()[:140])
                                )
                                break

        if not hits_by_file:
            print("No hits — solver may not reference requirement_type at all.")
            return
        for rel in sorted(hits_by_file):
            print(f"=== {rel} ===")
            for lineno, kw, line in hits_by_file[rel]:
                print(f"  {lineno:5d} [{kw:15s}] {line}")
            print()
