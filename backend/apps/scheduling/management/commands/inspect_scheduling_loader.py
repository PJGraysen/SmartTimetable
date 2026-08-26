from django.core.management.base import BaseCommand

from apps.scheduling.engine.infrastructure import django_loader


class Command(BaseCommand):
    help = "Inspect the Django scheduling loader exports used by the scheduling engine."

    def handle(self, *args, **options):
        self.stdout.write("\n=== DJANGO SCHEDULING LOADER ===\n")

        module = django_loader

        self.stdout.write(
            f"Module: {module.__file__}"
        )

        self.stdout.write("\n=== PUBLIC CALLABLES ===")

        for name in sorted(dir(module)):
            if name.startswith("_"):
                continue

            value = getattr(module, name)

            if callable(value):
                self.stdout.write(
                    f"{name} | {type(value).__name__}"
                )

        self.stdout.write(
            "\n=== INSPECTION COMPLETE ==="
        )
