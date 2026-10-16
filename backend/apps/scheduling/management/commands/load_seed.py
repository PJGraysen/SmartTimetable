"""Load backend/seed/data.json into the current database.

    python manage.py migrate
    python manage.py load_seed

Replaces all rows in the seeded models atomically. Refuses to run when
TimetableVersion / LessonRequirement / TeacherAssignment already have
rows unless --allow-existing is passed.
"""
from __future__ import annotations
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


# Dependency-ordered: children before parents.
_DELETE_ORDER = (
    "scheduling.TimetableEntry",
    "scheduling.TimetableVersion",
    "scheduling.TeacherAssignment",
    "scheduling.TeacherFreeAfternoon",
    "scheduling.TeacherAvailability",
    "scheduling.RoomAvailability",
    "scheduling.DutyAssignment",
    "scheduling.SchedulingRuleConfig",
    "academics.LessonRequirement",
    "academics.InstructionalGroup",
    "academics.TeachingGroup",
    "academics.Stream",
    "academics.Grade",
    "academics.RankingRule",
    "academics.GradingBand",
    "academics.GradingScheme",
    "academics.Subject",
    "scheduling.Period",
    "scheduling.Room",
    "users.Teacher",
    "core.SchoolEvent",
    "core.School",
    "core.Term",
    "core.AcademicYear",
)


class Command(BaseCommand):
    help = "Load the curated seed fixture into the current database"

    def add_arguments(self, parser):
        parser.add_argument("--input", default=None)
        parser.add_argument("--allow-existing", action="store_true")

    def handle(self, *args, **opts):
        in_path = Path(opts["input"]) if opts["input"] else (
            Path(settings.BASE_DIR) / "seed" / "data.json"
        )
        if not in_path.exists():
            raise CommandError(
                f"Seed fixture not found: {in_path}\n"
                "Generate it with `python manage.py dump_seed`.")

        if not opts["allow_existing"]:
            from apps.scheduling.models import (
                TimetableVersion, TeacherAssignment,
            )
            from apps.academics.models import LessonRequirement
            for M, label in (
                (TimetableVersion, "TimetableVersion"),
                (TeacherAssignment, "TeacherAssignment"),
                (LessonRequirement, "LessonRequirement"),
            ):
                n = M.objects.count()
                if n:
                    raise CommandError(
                        f"{label} already has {n} rows. Refusing to load "
                        "seed on a populated database. "
                        "Use --allow-existing to override.")

        from django.apps import apps as _apps

        self.stdout.write(f"Loading {in_path} ...")
        self.stdout.write(
            "  (replacing rows in the seeded models; migration-seeded "
            "lookups such as the default Subject are reset to the "
            "fixture's versions)")

        # ── Order matters here ───────────────────────────────────────────
        # SQLite refuses to change `PRAGMA foreign_keys` inside a live
        # transaction. Django's loaddata calls constraint_checks_disabled()
        # internally, but if we have already opened an atomic block it is
        # a no-op and every INSERT is FK-checked. The fixture inserts in
        # serializer order, which is not always dependency order, so the
        # check fires at COMMIT with a bare "FOREIGN KEY constraint failed".
        #
        # By wrapping constraint_checks_disabled() OUTSIDE the atomic block
        # we make the pragma apply. Cross-backend safe: on Postgres, the
        # same context manager runs SET CONSTRAINTS ALL DEFERRED.
        with connection.constraint_checks_disabled():
            with transaction.atomic():
                for label in _DELETE_ORDER:
                    app_label, name = label.split(".")
                    M = _apps.get_model(app_label, name)
                    n = M.objects.count()
                    if n:
                        M.objects.all().delete()
                        self.stdout.write(
                            f"  cleared {label:40s} {n:>6,}")

                call_command("loaddata", str(in_path))

            # Post-commit verification. If the fixture is self-consistent
            # this returns nothing; if not, we surface the exact rows.
            if connection.vendor == "sqlite":
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_key_check")
                    bad = cursor.fetchall()
                if bad:
                    raise CommandError(
                        f"Seed load left {len(bad)} dangling FK row(s). "
                        f"First few: {bad[:5]}")

        from apps.scheduling.models import TimetableVersion, TimetableEntry
        self.stdout.write(self.style.SUCCESS(
            f"\nLoaded. TimetableVersion count: "
            f"{TimetableVersion.objects.count()}  "
            f"TimetableEntry count: {TimetableEntry.objects.count()}"))
