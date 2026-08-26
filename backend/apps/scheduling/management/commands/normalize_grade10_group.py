from django.core.management.base import BaseCommand
from django.db import transaction

from apps.scheduling.models import LessonRequirement


class Command(BaseCommand):
    help = "Normalize the current single Grade 10 instructional group name."

    def handle(self, *args, **options):
        requirements = LessonRequirement.objects.select_related(
            "instructional_group"
        ).filter(
            instructional_group__name__in=[
                "Grade 10A",
                "Grade 10 - A",
                "Grade 10 - A - Grade 10A - Grade 10A",
            ]
        )

        groups = {}

        for requirement in requirements:
            groups[requirement.instructional_group.pk] = (
                requirement.instructional_group
            )

        if not groups:
            self.stdout.write(
                self.style.WARNING(
                    "No Grade 10A instructional group found. Nothing changed."
                )
            )
            return

        if len(groups) > 1:
            self.stdout.write(
                self.style.ERROR(
                    "ABORTED: Multiple possible Grade 10 groups were found. "
                    "No changes made."
                )
            )

            for group in groups.values():
                self.stdout.write(
                    f"  {group.pk} | {group.name}"
                )

            return

        group = next(iter(groups.values()))

        if group.name == "Grade 10":
            self.stdout.write(
                self.style.SUCCESS(
                    "Grade 10 instructional group is already correctly named."
                )
            )
            return

        with transaction.atomic():
            old_name = group.name
            group.name = "Grade 10"
            group.save(update_fields=["name", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Renamed instructional group: {old_name} -> Grade 10"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Teacher records and teacher codes were not changed."
            )
        )
