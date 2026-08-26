from django.core.management.base import BaseCommand

from apps.scheduling.models import TeacherFreeAfternoon


class Command(BaseCommand):
    help = "Inspect TeacherFreeAfternoon model fields and existing records."

    def handle(self, *args, **options):
        self.stdout.write(
            "\n=== TEACHER FREE-AFTERNOON MODEL ===\n"
        )

        for field in TeacherFreeAfternoon._meta.fields:
            self.stdout.write(
                f"{field.name} | "
                f"type={field.__class__.__name__} | "
                f"null={field.null} | "
                f"blank={field.blank} | "
                f"default={field.default}"
            )

        self.stdout.write(
            "\n=== EXISTING FREE-AFTERNOON RECORDS ===\n"
        )

        records = (
            TeacherFreeAfternoon.objects
            .select_related("teacher")
            .order_by("teacher__teacher_number")
        )

        for record in records:
            values = {}

            for field in TeacherFreeAfternoon._meta.fields:
                try:
                    value = getattr(record, field.name)

                    if hasattr(value, "employee_code"):
                        value = value.employee_code

                    values[field.name] = value
                except Exception:
                    values[field.name] = "<unavailable>"

            self.stdout.write(
                f"{record.pk} | {values}"
            )

        self.stdout.write(
            "\n=== READ-ONLY INSPECTION COMPLETE ==="
        )
