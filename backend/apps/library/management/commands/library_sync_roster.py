"""Sync platform Students/Teachers into Library Members."""
from django.core.management.base import BaseCommand
from apps.library.services.roster import sync_roster, eligible_people


class Command(BaseCommand):
    help = "Sync platform Students and Teachers into Library Members."
    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        if opts["dry_run"]:
            data = eligible_people()
            print(f"Students not yet members: {len(data['students'])}")
            for s in data["students"][:20]:
                print(f"  {s['admission_number']}  {s['first_name']} {s['last_name']}")
            print(f"Teachers not yet members: {len(data['teachers'])}")
            for t in data["teachers"][:20]:
                print(f"  {t['employee_code']}  {t['first_name']} {t['last_name']} ({t['role']})")
            print("\nDry run — re-run without --dry-run to write.")
            return
        result = sync_roster()
        print("Sync complete:")
        for k, v in result.items():
            print(f"  {k}: {v}")
