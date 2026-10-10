"""Seed test students for Grade 11E and 11W (curriculum testing).

Usage:
    python manage.py seed_grade11_students --dry-run
    python manage.py seed_grade11_students --commit
"""
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import (
    Student, StudentEnrollment, TeachingGroup,
)
from apps.core.models import AcademicYear


FIRST_NAMES_M = [
    "Brian", "Kevin", "Dennis", "Elvis", "Felix", "George", "Henry",
    "Ian", "Joseph", "Kelvin", "Lucas", "Martin", "Nathan", "Oscar",
    "Patrick", "Quinn", "Robert", "Samuel", "Timothy", "Victor",
]
FIRST_NAMES_F = [
    "Alice", "Brenda", "Cynthia", "Diana", "Esther", "Faith", "Grace",
    "Hannah", "Irene", "Joy", "Karen", "Lucy", "Mercy", "Nancy",
    "Olivia", "Patience", "Rita", "Sharon", "Tabitha", "Violet",
]
LAST_NAMES = [
    "Kimani", "Wanjiku", "Otieno", "Mwangi", "Kariuki", "Njoroge",
    "Odhiambo", "Muthoni", "Wambui", "Chebet", "Kipchoge", "Cheruiyot",
    "Achieng", "Onyango", "Njeri", "Mwende", "Barasa", "Wafula",
    "Kamau", "Nyambura",
]


class Command(BaseCommand):
    help = "Seed test students for Grade 11E and 11W."

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true")
        parser.add_argument("--per-stream", type=int, default=20)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        commit = opts["commit"] and not opts["dry_run"]
        per_stream = opts["per_stream"]

        year = AcademicYear.objects.filter(is_active=True).first()
        if not year:
            self.stderr.write("No active AcademicYear.")
            return

        targets = []
        for name in ("G11E", "G11W"):
            tg = TeachingGroup.objects.filter(name=name).first()
            if not tg:
                self.stderr.write(f"TeachingGroup {name} not found.")
                return
            targets.append(tg)

        plan = []
        admission = 2026001
        for tg in targets:
            for i in range(per_stream):
                first = (FIRST_NAMES_M + FIRST_NAMES_F)[(admission + i) % 40]
                last = LAST_NAMES[(admission + i) % len(LAST_NAMES)]
                plan.append({
                    "admission": str(admission),
                    "first": first,
                    "last": last,
                    "tg": tg,
                })
                admission += 1

        self.stdout.write(f"Plan: {len(plan)} students across G11E/W")
        for row in plan[:5]:
            self.stdout.write(f"  {row['admission']} {row['first']} {row['last']} -> {row['tg'].name}")
        self.stdout.write(f"  ... ({len(plan) - 5} more)")

        if not commit:
            self.stdout.write(self.style.WARNING("DRY-RUN. Add --commit."))
            return

        created = 0
        with transaction.atomic():
            for row in plan:
                # Skip if admission exists
                if Student.objects.filter(admission_number=row["admission"]).exists():
                    continue
                s = Student.objects.create(
                    admission_number=row["admission"],
                    first_name=row["first"],
                    last_name=row["last"],
                    is_active=True,
                )
                StudentEnrollment.objects.create(
                    student=s,
                    teaching_group=row["tg"],
                    academic_year=year,
                    joined_on=date.today(),
                    is_current=True,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} students."))
