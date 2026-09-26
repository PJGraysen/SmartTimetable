"""Register every BookCopy as an inventory Asset under LIBRARY department."""
from django.core.management.base import BaseCommand
from apps.library.services.inventory_link import register_all_copies


class Command(BaseCommand):
    help = "Create inventory Assets for all BookCopies not yet linked."
    def handle(self, *args, **opts):
        result = register_all_copies()
        print("Inventory link complete:")
        for k, v in result.items():
            print(f"  {k}: {v}")
