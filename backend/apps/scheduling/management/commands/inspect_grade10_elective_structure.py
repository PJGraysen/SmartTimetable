from django.core.management.base import BaseCommand

from apps.academics.models import Subject
from apps.scheduling.models import LessonRequirement


class Command(BaseCommand):
    help = "Read-only inspection of the authoritative Grade 10 elective structure."

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(
            "SMARTTIMETABLE PRO - GRADE 10 ELECTIVE STRUCTURE INSPECTION"
        )
        self.stdout.write("=" * 80)
        self.stdout.write("")
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES WILL BE MADE.")
        self.stdout.write("")

        groups = (
            LessonRequirement.objects
            .select_related("instructional_group", "subject", "term")
            .filter(
                instructional_group__name__in=[
                    "Grade 10E",
                    "Grade 10W",
                ]
            )
            .order_by(
                "instructional_group__name",
                "subject__code",
            )
        )

        expected_blocks = {
            "OPTION_1": ["BIO", "MUS", "FRE"],
            "OPTION_2": ["CHEM", "PHY", "LIT"],
            "OPTION_3": ["GEO", "HIS", "CS"],
            "OPTION_4": ["BUS", "AGR"],
        }

        self.stdout.write("EXPECTED AUTHORITATIVE ELECTIVE BLOCKS")
        self.stdout.write("-" * 80)

        for block_name, codes in expected_blocks.items():
            self.stdout.write(
                f"{block_name}: {' / '.join(codes)} = 5 shared timetable slots/week"
            )

        self.stdout.write("")
        self.stdout.write("DATABASE REQUIREMENTS")
        self.stdout.write("-" * 80)

        seen = set()

        for requirement in groups:
            group_name = requirement.instructional_group.name
            subject = requirement.subject

            code = getattr(subject, "code", None) or "UNKNOWN"
            name = getattr(subject, "name", None) or str(subject)

            active = getattr(requirement, "active", None)

            weekly = (
                getattr(requirement, "lessons_per_week", None)
                if hasattr(requirement, "lessons_per_week")
                else getattr(requirement, "periods_per_week", None)
            )

            key = (group_name, code)

            if key in seen:
                continue

            seen.add(key)

            self.stdout.write(
                f"{group_name:<10} | "
                f"{code:<8} | "
                f"{name:<45} | "
                f"active={active!s:<5} | "
                f"weekly={weekly}"
            )

        self.stdout.write("")
        self.stdout.write("MODEL FIELD INSPECTION")
        self.stdout.write("-" * 80)

        self.stdout.write("LessonRequirement fields:")

        for field in LessonRequirement._meta.get_fields():
            self.stdout.write(
                f"  {field.name:<35} | "
                f"{field.__class__.__name__:<30} | "
                f"relation={getattr(field, 'related_model', None)}"
            )

        self.stdout.write("")
        self.stdout.write("Subject fields:")

        for field in Subject._meta.get_fields():
            self.stdout.write(
                f"  {field.name:<35} | "
                f"{field.__class__.__name__:<30} | "
                f"relation={getattr(field, 'related_model', None)}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write("END READ-ONLY ELECTIVE STRUCTURE INSPECTION")
        self.stdout.write("=" * 80)
