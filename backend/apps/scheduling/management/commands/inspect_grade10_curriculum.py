from django.core.management.base import BaseCommand
from apps.scheduling.models import LessonRequirement
from apps.academics.models import Subject


class Command(BaseCommand):
    help = "Inspect all current subjects and their fields before Grade 10 curriculum synchronization."

    def handle(self, *args, **options):
        self.stdout.write("\n=== SUBJECT MODEL FIELDS ===\n")

        for field in Subject._meta.fields:
            self.stdout.write(
                f"{field.name} | "
                f"type={field.__class__.__name__} | "
                f"null={field.null} | "
                f"blank={field.blank} | "
                f"default={field.default}"
            )

        self.stdout.write("\n=== EXISTING SUBJECTS ===\n")

        for subject in Subject.objects.all().order_by("name"):
            values = {}

            for field in subject._meta.fields:
                try:
                    value = getattr(subject, field.name)

                    if hasattr(value, "pk"):
                        value = f"{value} [pk={value.pk}]"

                    values[field.name] = value
                except Exception:
                    values[field.name] = "<unavailable>"

            self.stdout.write(
                f"{subject.pk} | {values}"
            )

        self.stdout.write("\n=== CURRENT ACTIVE GRADE 10 REQUIREMENTS ===\n")

        requirements = (
            LessonRequirement.objects
            .select_related("subject", "instructional_group")
            .filter(
                instructional_group__name="Grade 10",
                is_active=True,
            )
            .order_by("subject__name")
        )

        for requirement in requirements:
            self.stdout.write(
                f"{requirement.subject.name} | "
                f"{requirement.lessons_per_week}/week | "
                f"{requirement.subject.pk}"
            )

        self.stdout.write(
            "\n=== READ-ONLY INSPECTION COMPLETE ==="
        )
