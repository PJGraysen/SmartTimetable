from django.core.management.base import BaseCommand
from apps.scheduling.engine.solver import model as M
import inspect, ast, pathlib

class Command(BaseCommand):
    help = "Find the method that contains the Grade 10 parallel-block loop"
    def handle(self, *a, **kw):
        path = pathlib.Path(M.__file__)
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)

        cls = next(
            (n for n in ast.walk(tree)
             if isinstance(n, ast.ClassDef) and n.name == "SolverModelBuilder"),
            None,
        )
        if not cls:
            print("SolverModelBuilder class not found"); return

        print(f"File: {path}")
        print(f"Class spans lines {cls.lineno}..{cls.end_lineno}")
        print()

        # Methods and line ranges
        methods = []
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append((node.name, node.lineno, node.end_lineno))
        methods.sort(key=lambda m: m[1])

        print("=== Methods ===")
        for name, lo, hi in methods:
            marker = ""
            if 1080 <= lo <= 1090 or 1080 <= hi <= 1090:
                marker = "  <<< contains line 1084"
            print(f"  {lo:5d}..{hi:5d}  {name}{marker}")
        print()

        # Which method contains line 1084?
        target = 1084
        for name, lo, hi in methods:
            if lo <= target <= hi:
                print(f"=== Target method: {name} (lines {lo}..{hi}) ===")
                fn = getattr(M.SolverModelBuilder, name, None)
                if fn:
                    try:
                        print(inspect.getsource(fn))
                    except Exception as e:
                        print(f"  (no source: {e})")
                break

        print()
        print("=== Methods that mention GRADE10_PARALLEL_BLOCKS ===")
        for name, lo, hi in methods:
            segment = "\n".join(src.splitlines()[lo-1:hi])
            if "GRADE10_PARALLEL_BLOCKS" in segment:
                print(f"  {name}  (lines {lo}..{hi})")
