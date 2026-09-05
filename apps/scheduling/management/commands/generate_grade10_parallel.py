from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max

from apps.core.models import Term
from apps.scheduling.models import SchedulingRun, TimetableVersion
from apps.scheduling.engine.application.scheduling_application import (
    SchedulingApplicationService,
)
from apps.scheduling.engine.application.scheduler import (
    create_default_scheduler,
)
from apps.scheduling.engine.domain.enums import SchedulingRunStatus


class Command(BaseCommand):
    help = (
        "Generate a new timetable using the authoritative Grade 10 "
        "parallel-elective solver model."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--term",
            default="8ba158ac-4526-41d6-bf40-cb30023e09eb",
        )
        parser.add_argument(
            "--time-limit",
            type=float,
            default=180.0,
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=8,
        )

    def handle(self, *args, **options):
        term_id = options["term"]
        time_limit = options["time_limit"]
        workers = options["workers"]

        try:
            term = Term.objects.get(pk=term_id)
        except Term.DoesNotExist as exc:
            raise CommandError(
                f"Academic term not found: {term_id}"
            ) from exc

        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write(
            "SMARTTIMETABLE PRO — NEW GRADE 10 PARALLEL ELECTIVE GENERATION"
        )
        self.stdout.write("=" * 100)
        self.stdout.write(f"TERM:        {term}")
        self.stdout.write(f"TIME LIMIT:  {time_limit}s")
        self.stdout.write(f"WORKERS:     {workers}")
        self.stdout.write("")

        latest_version_number = (
            TimetableVersion.objects
            .filter(term=term)
            .aggregate(max_number=Max("version_number"))
            .get("max_number")
        )

        next_version_number = (
            int(latest_version_number or 0) + 1
        )

        existing_names = set(
            TimetableVersion.objects
            .filter(term=term)
            .values_list("name", flat=True)
        )

        name_number = next_version_number
        version_name = (
            f"Generated Timetable Parallel Elective v{name_number}"
        )

        while version_name in existing_names:
            name_number += 1
            version_name = (
                f"Generated Timetable Parallel Elective v{name_number}"
            )

        scheduling_run = SchedulingRun.objects.create(
            term=term,
            status=SchedulingRunStatus.PENDING,
        )

        self.stdout.write(
            f"RUN CREATED: {scheduling_run.id}"
        )
        self.stdout.write(
            f"VERSION:     {version_name}"
        )
        self.stdout.write(
            f"VERSION NO:  {next_version_number}"
        )
        self.stdout.write("")
        self.stdout.write(
            "Executing the production SchedulingApplicationService..."
        )
        self.stdout.write("")

        scheduler = create_default_scheduler(
            time_limit_seconds=time_limit,
            num_workers=workers,
        )

        service = SchedulingApplicationService(
            scheduler=scheduler,
        )

        try:
            result = service.execute(
                scheduling_run=scheduling_run,
                version_name=version_name,
                version_number=next_version_number,
            )
        except Exception as exc:
            scheduling_run.refresh_from_db()

            self.stdout.write("")
            self.stdout.write("=" * 100)
            self.stdout.write("GENERATION EXCEPTION")
            self.stdout.write("=" * 100)
            self.stdout.write(str(exc))
            self.stdout.write("")
            self.stdout.write(
                f"RUN:    {scheduling_run.id}"
            )
            self.stdout.write(
                f"STATUS: {scheduling_run.status}"
            )
            self.stdout.write(
                f"ERROR:  {scheduling_run.error_message}"
            )
            raise

        scheduling_run.refresh_from_db()

        solver_result = result.solver_result
        persistence_result = result.persistence_result

        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write("GENERATION RESULT")
        self.stdout.write("=" * 100)
        self.stdout.write(
            f"RUN:              {scheduling_run.id}"
        )
        self.stdout.write(
            f"FINAL STATUS:     {scheduling_run.status}"
        )
        self.stdout.write(
            f"SOLVER STATUS:    {scheduling_run.solver_status}"
        )
        self.stdout.write(
            f"OBJECTIVE:        {scheduling_run.objective_value}"
        )
        self.stdout.write(
            f"ERROR:            {scheduling_run.error_message!r}"
        )
        self.stdout.write(
            f"STATISTICS:       {scheduling_run.statistics}"
        )

        if persistence_result is not None:
            version = getattr(
                persistence_result,
                "timetable_version",
                None,
            )

            if version is not None:
                self.stdout.write(
                    f"TIMETABLE VERSION: {version.id}"
                )
                self.stdout.write(
                    f"VERSION NAME:      {version.name}"
                )
                self.stdout.write(
                    f"VERSION NUMBER:    {version.version_number}"
                )

        if solver_result is not None:
            self.stdout.write(
                f"ASSIGNMENTS:       {len(solver_result.assignments)}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 100)

        if not result.solver_result or not result.solver_result.is_successful:
            raise CommandError(
                "The new production scheduling run did not succeed."
            )

        if scheduling_run.timetable_version_id is None:
            raise CommandError(
                "Solver succeeded but no timetable version was persisted."
            )

        self.stdout.write(
            "NEW TIMETABLE GENERATED AND PERSISTED."
        )
        self.stdout.write(
            "No existing timetable version was modified."
        )
        self.stdout.write("=" * 100)
        self.stdout.write("")