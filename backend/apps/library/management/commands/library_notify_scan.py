"""Daily scan: emit due-soon + overdue notifications."""
from django.core.management.base import BaseCommand
from apps.library.services.notifications import scan_due_and_overdue


class Command(BaseCommand):
    help = "Scan active loans and generate due-soon/overdue notifications."
    def add_arguments(self, p):
        p.add_argument("--days", type=int, default=3)
    def handle(self, *a, **opts):
        result = scan_due_and_overdue(due_soon_days=opts["days"])
        self.stdout.write(f"due_soon={result['due_soon']} overdue={result['overdue']}")
