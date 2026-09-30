from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
import os


class Command(BaseCommand):
    help = (
        "Idempotent production bootstrap: create superuser from env vars, "
        "verify DB connectivity. Safe to run on every deploy."
    )

    def handle(self, *args, **opts):
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not password:
            self.stdout.write(
                self.style.WARNING(
                    "[BOOTSTRAP] DJANGO_SUPERUSER_PASSWORD not set; skipping superuser creation."
                )
            )
            return

        with transaction.atomic():
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.SUCCESS(f"[BOOTSTRAP] Superuser '{username}' already exists.")
                )
                return
            User.objects.create_superuser(
                username=username, email=email, password=password,
            )
        self.stdout.write(
            self.style.SUCCESS(f"[BOOTSTRAP] Superuser '{username}' created.")
        )
