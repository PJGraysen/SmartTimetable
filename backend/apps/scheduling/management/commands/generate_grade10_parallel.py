from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Term
from apps.scheduling.models import SchedulingRun
from apps.scheduling.engine.application.scheduler import create_default_scheduler
from apps.scheduling.engine.application.scheduling_application import (
    SchedulingApplicationService,
)


class Command(BaseCommand):
    help = "Generate a new Grade 10 timetable using the current production scheduling pipeline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--term",
            required=True,
        )
        parser.add_argument(
            "--time-limit",
            type=float,
            default=900.0,
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=16,
        )

    def handle(self, *args, **options):
        term_id = options["term"]
        time_limit = options["time_limit"]
        workers = options["workers"]

        try:
            term = Term.objects.get(pk=term_id)
        except Term.DoesNotExist as exc:
            raise CommandError(
                f"Term {term_id} does not exist."
            ) from exc

        previous_run_ids = set(
            SchedulingRun.objects.values_list("id", flat=True)
        )

        previous_versions = list(
            SchedulingRun.objects.exclude(
                timetable_version__isnull=True
            ).values_list(
                "timetable_version__version_number",
                flat=True,
            )
        )

        numeric_versions = [
            int(value)
            for value in previous_versions
            if value is not None
        ]

        next_version_number = (
            max(numeric_versions) + 1
            if numeric_versions
            else 1
        )

        version_name = f"Generated Timetable v{next_version_number}"

        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write(
            "SMARTTIMETABLE PRO — GRADE 10 PARALLEL ELECTIVE GENERATION"
        )
        self.stdout.write("=" * 100)
        self.stdout.write(f"TERM: {term_id}")
        self.stdout.write(f"TIME LIMIT: {time_limit} seconds")
        self.stdout.write(f"WORKERS: {workers}")
        self.stdout.write(f"VERSION: {version_name}")
        self.stdout.write("")

        scheduling_run = SchedulingRun.objects.create(
            term=term,
        )

        self.stdout.write(f"NEW RUN CREATED: {scheduling_run.id}")
        self.stdout.write("")
        self.stdout.write("Starting CP-SAT...")
        self.stdout.write("")

        scheduler = create_default_scheduler(
            time_limit_seconds=time_limit,
            num_workers=workers,
        )

        service = SchedulingApplicationService(
            scheduler=scheduler,
        )

        service.execute(
            scheduling_run=scheduling_run,
            version_name=version_name,
            version_number=next_version_number,
        )

        scheduling_run.refresh_from_db()

        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write("NEW RUN RESULT")
        self.stdout.write("=" * 100)
        self.stdout.write(f"RUN_ID: {scheduling_run.id}")
        self.stdout.write(f"STATUS: {scheduling_run.status}")
        self.stdout.write(f"SOLVER_STATUS: {scheduling_run.solver_status}")
        self.stdout.write(
            f"VERSION_ID: {scheduling_run.timetable_version_id}"
        )
        self.stdout.write(
            f"OBJECTIVE: {scheduling_run.objective_value}"
        )
        self.stdout.write(
            f"ERROR: {scheduling_run.error_message!r}"
        )
        self.stdout.write(
            f"STATISTICS: {scheduling_run.statistics}"
        )
        self.stdout.write("")

        status = str(scheduling_run.status).upper()
        solver_status = str(scheduling_run.solver_status).upper()

        if (
            "UNKNOWN" in status
            or "UNKNOWN" in solver_status
        ):
            raise CommandError(
                "CP-SAT returned UNKNOWN. No new timetable version was "
                "accepted. The authoritative audit must not be interpreted "
                "as validating this run."
            )

        if (
            "FAILED" in status
            or "FAILED" in solver_status
            or "INFEASIBLE" in status
            or "INFEASIBLE" in solver_status
        ):
            raise CommandError(
                "Generation did not produce a valid timetable version."
            )

        if scheduling_run.timetable_version_id is None:
            raise CommandError(
                "Generation completed without creating a timetable version."
            )

        self.stdout.write("=" * 100)
        self.stdout.write("NEW TIMETABLE VERSION ACCEPTED BY GENERATION PIPELINE")
        self.stdout.write("=" * 100)
        self.stdout.write(
            f"RUN_ID={scheduling_run.id}"
        )
        self.stdout.write(
            f"VERSION_ID={scheduling_run.timetable_version_id}"
        )