from django.core.management.base import BaseCommand

from apps.scheduling.models import (
    Period,
    TimetableEntry,
)


class Command(BaseCommand):
    help = (
        "Inspect the actual Period and TimetableEntry Django models "
        "and determine how timetable days are represented."
    )

    def handle(self, *args, **options):

        # ------------------------------------------------------------
        # PERIOD
        # ------------------------------------------------------------
        self.stdout.write(
            "\n=== PERIOD MODEL FIELDS ===\n"
        )

        for field in Period._meta.fields:
            related = getattr(
                field.remote_field,
                "model",
                None,
            )

            self.stdout.write(
                f"{field.name} | "
                f"type={field.__class__.__name__} | "
                f"related_model={related}"
            )

        # ------------------------------------------------------------
        # TIMETABLE ENTRY
        # ------------------------------------------------------------
        self.stdout.write(
            "\n=== TIMETABLE ENTRY MODEL FIELDS ===\n"
        )

        for field in TimetableEntry._meta.fields:
            related = getattr(
                field.remote_field,
                "model",
                None,
            )

            self.stdout.write(
                f"{field.name} | "
                f"type={field.__class__.__name__} | "
                f"related_model={related}"
            )

        # ------------------------------------------------------------
        # PERIOD RECORDS
        # ------------------------------------------------------------
        self.stdout.write(
            "\n=== EXISTING PERIODS ==="
        )

        periods = (
            Period.objects
            .all()
            .order_by("number")
        )

        self.stdout.write(
            f"Period count: {periods.count()}"
        )

        for period in periods:
            values = []

            for field in Period._meta.fields:
                try:
                    value = getattr(
                        period,
                        field.name,
                    )

                    if hasattr(value, "name"):
                        value = value.name

                    values.append(
                        f"{field.name}={value}"
                    )

                except Exception:
                    values.append(
                        f"{field.name}=<unavailable>"
                    )

            self.stdout.write(
                " | ".join(values)
            )

        # ------------------------------------------------------------
        # TIMETABLE ENTRIES
        # ------------------------------------------------------------
        self.stdout.write(
            "\n=== EXISTING TIMETABLE ENTRIES ==="
        )

        entries = (
            TimetableEntry.objects
            .select_related(
                "teacher",
                "period",
            )
            .all()
        )

        self.stdout.write(
            f"Entry count: {entries.count()}"
        )

        for entry in entries:

            values = []

            for field in TimetableEntry._meta.fields:
                try:
                    value = getattr(
                        entry,
                        field.name,
                    )

                    if hasattr(value, "employee_code"):
                        value = value.employee_code

                    elif hasattr(value, "name"):
                        value = value.name

                    values.append(
                        f"{field.name}={value}"
                    )

                except Exception:
                    values.append(
                        f"{field.name}=<unavailable>"
                    )

            self.stdout.write(
                " | ".join(values)
            )

        self.stdout.write(
            "\n=== READ-ONLY INSPECTION COMPLETE ==="
        )
