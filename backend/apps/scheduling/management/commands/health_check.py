from django.core.management.base import BaseCommand
from django.core.management import call_command
from contextlib import redirect_stdout
from io import StringIO
import sys


CHECKS = [
    ("Block-aware compliance",        "audit_blockaware",      "ALL CLASSES OK"),
    ("Teacher load (distinct slots)", "audit_teacher_slots",   "Teachers over 46: NONE"),
]


class Command(BaseCommand):
    help = "Run all scheduling audits and print overall PASS/FAIL"

    def handle(self, *args, **opts):
        results = []
        for label, cmd, pass_marker in CHECKS:
            buf = StringIO()
            try:
                with redirect_stdout(buf):
                    call_command(cmd)
                out = buf.getvalue()
                ok = pass_marker in out
            except Exception as e:
                out = f"<error: {e}>"
                ok = False
            results.append((label, ok, out))

        print("=" * 60)
        print("SCHEDULING HEALTH CHECK")
        print("=" * 60)
        for label, ok, out in results:
            tag = "PASS" if ok else "FAIL"
            print(f"[{tag}] {label}")

        # Soft pedagogical rules (newest version)
        from io import StringIO as _SIO2
        from contextlib import redirect_stdout as _RSO2
        _buf2 = _SIO2()
        try:
            with _RSO2(_buf2):
                call_command("audit_new_rules")
            _out2 = _buf2.getvalue()
            _adj_ok = "adjacency=0" in _out2
            _am_ok = "maths_afternoon=0" in _out2
            if _adj_ok and _am_ok:
                _tag2 = "PASS"
            elif _adj_ok or _am_ok:
                _tag2 = "WARN"
            else:
                _tag2 = "WARN"
            print(f"[{_tag2}] Complex-adjacency + maths-morning (soft rules)")
            if _tag2 != "PASS":
                # Show the summary line only
                for _ln in _out2.splitlines():
                    if _ln.startswith("RESULT:"):
                        print(f"        {_ln}")
        except Exception as _e2:
            print(f"[FAIL] Complex-adjacency + maths-morning: {_e2}")

        all_ok = all(ok for _, ok, _ in results)
        print()
        print("OVERALL:", "PASS" if all_ok else "FAIL")
        if not all_ok:
            sys.exit(1)
