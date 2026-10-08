"""
Migrate current-student enrollments to their next-year teaching group.

Mapping (2026 rollover):
  Grade 8E  -> Grade 9E   (all)
  Form 3E   -> Form 4E    (all)
  Form 3W   -> Form 4W    (all)

Preserves history: old enrollment is marked is_current=False and a new
enrollment is created for the destination group. Idempotent — if a student
already has a current enrollment in the destination, the source enrollment
is just deactivated.

Usage:
    python manage.py migrate_student_enrollments --dry-run
    python manage.py migrate_student_enrollments --commit
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import (
    StudentEnrollment,
    TeachingGroup,
)


MAPPING = (
    ("Grade 8E", "Grade 9E"),
    ("Form 3E",  "Form 4E"),
    ("Form 3W",  "Form 4W"),
)


class Command(BaseCommand):
    help = "Roll over current students to their next-year teaching group."

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true",
                            help="Actually write to the database (default: dry-run).")
        parser.add_argument("--dry-run", action="store_true",
                            help="Explicit dry-run (default).")

    def handle(self, *args, **options):
        commit = bool(options["commit"]) and not options["dry_run"]

        plan = []
        errors = []

        for src_name, dst_name in MAPPING:
            src = TeachingGroup.objects.filter(name=src_name).first()
            dst = TeachingGroup.objects.filter(name=dst_name).first()

            if src is None:
                errors.append(f"Source teaching group not found: {src_name}")
                continue
            if dst is None:
                errors.append(f"Destination teaching group not found: {dst_name}")
                continue

            enrollments = list(
                StudentEnrollment.objects.filter(
                    teaching_group=src, is_current=True,
                ).select_related("student")
            )

            already_there = set(
                StudentEnrollment.objects.filter(
                    teaching_group=dst, is_current=True,
                ).values_list("student_id", flat=True)
            )

            for e in enrollments:
                plan.append({
                    "student": e.student,
                    "source_enrollment": e,
                    "source": src,
                    "dest": dst,
                    "skip_create": e.student_id in already_there,
                })

        if errors:
            for e in errors:
                self.stderr.write(self.style.ERROR(f"  ! {e}"))
            return

        # ---- Report ----
        self.stdout.write("Migration plan:")
        self.stdout.write("")
        per_pair: dict = {}
        for row in plan:
            key = (row["source"].name, row["dest"].name)
            per_pair.setdefault(key, {"total": 0, "skipped": 0})
            per_pair[key]["total"] += 1
            if row["skip_create"]:
                per_pair[key]["skipped"] += 1

        for (src, dst), counts in per_pair.items():
            self.stdout.write(
                f"  {src:12s} -> {dst:12s} : "
                f"{counts['total']:3d} students "
                f"({counts['skipped']} already in destination)"
            )

        self.stdout.write("")
        self.stdout.write("Student preview (first 10):")
        for row in plan[:10]:
            flag = " [SKIP-CREATE]" if row["skip_create"] else ""
            self.stdout.write(
                f"  {row['student'].full_name:35s} : "
                f"{row['source'].name} -> {row['dest'].name}{flag}"
            )
        if len(plan) > 10:
            self.stdout.write(f"  ... ({len(plan) - 10} more)")

        self.stdout.write("")
        self.stdout.write(f"Total moves: {len(plan)}")

        if not commit:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "DRY-RUN. Re-run with --commit to write."
            ))
            return

        # ---- Commit ----
        created = 0
        deactivated = 0
        skipped = 0

        with transaction.atomic():
            for row in plan:
                src_enr = row["source_enrollment"]

                if src_enr.is_current:
                    src_enr.is_current = False
                    src_enr.save(update_fields=["is_current"])
                    deactivated += 1

                if row["skip_create"]:
                    skipped += 1
                    continue

                # Reuse source enrollment's academic_year and joined_on
                # so history stays consistent. If the source had neither
                # (shouldn't happen), fall back to today.
                from datetime import date as _date
                source_enr = row["source_enrollment"]
                StudentEnrollment.objects.create(
                    student=row["student"],
                    academic_year=source_enr.academic_year,
                    teaching_group=row["dest"],
                    joined_on=source_enr.joined_on or _date.today(),
                    is_current=True,
                )
                created += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Deactivated {deactivated} old enrollments."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Created {created} new enrollments."
        ))
        if skipped:
            self.stdout.write(self.style.WARNING(
                f"Skipped {skipped} (student already in destination)."
            ))
