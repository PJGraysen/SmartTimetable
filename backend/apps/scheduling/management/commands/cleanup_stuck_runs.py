"""Mark long-running RUNNING scheduling runs as FAILED."""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone


def _run_model():
    from django.apps import apps
    for m in apps.get_models():
        if m.__name__ == "SchedulingRun":
            return m


class Command(BaseCommand):
    help = "Mark RUNNING scheduling runs older than N minutes as FAILED."
    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=30)
        parser.add_argument("--commit", action="store_true")

    def handle(self, *args, **opts):
        R = _run_model()
        cutoff = timezone.now() - timedelta(minutes=opts["minutes"])
        stuck = R.objects.filter(status="RUNNING", created_at__lt=cutoff)
        n = stuck.count()
        self.stdout.write(f"Stuck RUNNING runs older than {opts['minutes']} min: {n}")
        for r in stuck[:10]:
            self.stdout.write(f"  {str(r.id)[:8]}  created={r.created_at}  solver_status={r.solver_status}")
        if not opts["commit"]:
            self.stdout.write("\nDRY RUN — pass --commit to write")
            return
        stuck.update(
            status="FAILED",
            solver_status="TIMEOUT",
            completed_at=timezone.now(),
            error_message="Marked FAILED by cleanup_stuck_runs",
        )
        self.stdout.write(f"\nMarked {n} runs as FAILED")
