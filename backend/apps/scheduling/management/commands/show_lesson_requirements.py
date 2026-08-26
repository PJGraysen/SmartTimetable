from django.core.management.base import BaseCommand

from apps.scheduling.models import LessonRequirement


class Command(BaseCommand):
    help = "Display all instructional groups and their active lesson requirements."

    def handle(self, *args, **options):
        self.stdout.write("\n=== ACTIVE LESSON REQUIREMENTS BY INSTRUCTIONAL GROUP ===\n")

        requirements = (
            LessonRequirement.objects
            .select_related(
                "instructional_group",
                "subject",
                "term",
            )
            .filter(is_active=True)
            .order_by(
                "instructional_group__name",
                "subject__name",
            )
        )

        current_group = None

        for requirement in requirements:
            group_name = requirement.instructional_group.name

            if group_name != current_group:
                current_group = group_name

                self.stdout.write(
                    f"\n--- {group_name} ---"
                )

            self.stdout.write(
                f"  {requirement.subject.name} | "
                f"{requirement.lessons_per_week}/week | "
                f"Requirement={requirement.pk}"
            )

        self.stdout.write(
            "\n\n=== END: NO DATABASE CHANGES WERE MADE ==="
        )
