
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Read-only inventory of TimetableVersions and SchedulingRuns."


class Command(BaseCommand):
    help = "Read-only inventory of timetable versions and scheduling runs."

    def handle(self, *args, **options):
        from apps.scheduling.models import TimetableVersion, SchedulingRun

        self.stdout.write("")
        self.stdout.write("=" * 120)
        self.stdout.write(
            "SMARTTIMETABLE PRO - TIMETABLE VERSION / SCHEDULING RUN INVENTORY"
        )
        self.stdout.write("=" * 120)
        self.stdout.write("READ-ONLY: no database records are modified.")
        self.stdout.write("")

        # ==============================================================
        # MODEL STRUCTURE
        # ==============================================================
        self.stdout.write("=" * 120)
        self.stdout.write("1. TIMETABLE VERSION MODEL")
        self.stdout.write("=" * 120)

        self.describe_model(TimetableVersion)

        self.stdout.write("")
        self.stdout.write("=" * 120)
        self.stdout.write("2. SCHEDULING RUN MODEL")
        self.stdout.write("=" * 120)

        self.describe_model(SchedulingRun)

        # ==============================================================
        # ALL TIMETABLE VERSIONS
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 120)
        self.stdout.write("3. ALL TIMETABLE VERSIONS")
        self.stdout.write("=" * 120)

        versions = list(
            TimetableVersion.objects
            .select_related("term")
            .order_by("-version_number", "-created_at", "-pk")
        )

        self.stdout.write(
            f"TOTAL TIMETABLE VERSIONS: {len(versions)}"
        )

        for version in versions:
            entry_count = version.entries.count()

            run_count = version.scheduling_runs.count()

            self.stdout.write(
                f"ID={version.pk} | "
                f"VERSION_NUMBER={version.version_number} | "
                f"NAME={version.name} | "
                f"TERM={getattr(version.term, 'name', version.term)} | "
                f"ENTRIES={entry_count} | "
                f"RUNS={run_count} | "
                f"ACTIVE={version.is_active} | "
                f"PUBLISHED={version.is_published} | "
                f"CREATED={version.created_at}"
            )

        # ==============================================================
        # VERSIONS AROUND 82
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 120)
        self.stdout.write("4. VERSIONS AROUND 82")
        self.stdout.write("=" * 120)

        around_82 = [
            version
            for version in versions
            if 75 <= int(version.version_number) <= 90
        ]

        if not around_82:
            self.stdout.write(
                "NO timetable versions numbered 75 through 90 were found."
            )
        else:
            for version in around_82:
                self.stdout.write(
                    f"VERSION_NUMBER={version.version_number} | "
                    f"NAME={version.name} | "
                    f"ID={version.pk} | "
                    f"ENTRIES={version.entries.count()} | "
                    f"CREATED={version.created_at}"
                )

        # ==============================================================
        # NAMES CONTAINING 82
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 120)
        self.stdout.write("5. TIMETABLE VERSIONS WHOSE NAME CONTAINS '82'")
        self.stdout.write("=" * 120)

        named_82 = list(
            TimetableVersion.objects
            .filter(name__icontains="82")
            .select_related("term")
            .order_by("-created_at")
        )

        if not named_82:
            self.stdout.write(
                "NO TimetableVersion names containing '82' were found."
            )
        else:
            for version in named_82:
                self.stdout.write(
                    f"VERSION_NUMBER={version.version_number} | "
                    f"NAME={version.name} | "
                    f"ID={version.pk} | "
                    f"ENTRIES={version.entries.count()} | "
                    f"CREATED={version.created_at}"
                )

        # ==============================================================
        # SCHEDULING RUNS
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 120)
        self.stdout.write("6. RECENT SCHEDULING RUNS")
        self.stdout.write("=" * 120)

        run_fields = {
            field.name
            for field in SchedulingRun._meta.get_fields()
        }

        runs = list(
            SchedulingRun.objects
            .select_related("timetable_version")
            .order_by("-created_at", "-pk")[:50]
        )

        self.stdout.write(
            f"SHOWING {len(runs)} MOST RECENT RUNS"
        )

        for run in runs:
            version = getattr(run, "timetable_version", None)

            values = [
                f"RUN_ID={run.pk}",
            ]

            for field in [
                "status",
                "created_at",
                "started_at",
                "completed_at",
                "solver_status",
                "message",
            ]:
                if field in run_fields:
                    values.append(
                        f"{field.upper()}={getattr(run, field, None)}"
                    )

            if version:
                values.extend([
                    f"VERSION_ID={version.pk}",
                    f"VERSION_NUMBER={version.version_number}",
                    f"VERSION_NAME={version.name}",
                    f"VERSION_ENTRIES={version.entries.count()}",
                ])

            self.stdout.write(" | ".join(values))

        # ==============================================================
        # POSSIBLE "82" REFERENCES IN RUNS
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 120)
        self.stdout.write("7. SCHEDULING RUNS / VERSIONS ASSOCIATED WITH '82'")
        self.stdout.write("=" * 120)

        matches = []

        for run in runs:
            version = getattr(run, "timetable_version", None)

            text = " ".join(
                str(value)
                for value in [
                    run.pk,
                    getattr(run, "status", ""),
                    getattr(run, "solver_status", ""),
                    getattr(run, "message", ""),
                    getattr(version, "pk", ""),
                    getattr(version, "version_number", ""),
                    getattr(version, "name", ""),
                ]
            )

            if "82" in text:
                matches.append((run, version))

        if not matches:
            self.stdout.write(
                "No recent scheduling run/version record containing '82' was found."
            )
        else:
            for run, version in matches:
                self.stdout.write(
                    f"RUN={run.pk} | "
                    f"VERSION={getattr(version, 'version_number', '-')} | "
                    f"NAME={getattr(version, 'name', '-')} | "
                    f"STATUS={getattr(run, 'status', '-')} | "
                    f"CREATED={getattr(run, 'created_at', '-')}"
                )

        # ==============================================================
        # ACTIVE / PUBLISHED
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 120)
        self.stdout.write("8. ACTIVE / PUBLISHED TIMETABLE VERSIONS")
        self.stdout.write("=" * 120)

        active = list(
            TimetableVersion.objects
            .filter(is_active=True)
            .select_related("term")
            .order_by("-version_number", "-created_at")
        )

        published = list(
            TimetableVersion.objects
            .filter(is_published=True)
            .select_related("term")
            .order_by("-version_number", "-created_at")
        )

        self.stdout.write("")
        self.stdout.write("ACTIVE:")
        for version in active:
            self.stdout.write(
                f"  v{version.version_number} | "
                f"{version.name} | "
                f"ENTRIES={version.entries.count()} | "
                f"CREATED={version.created_at}"
            )

        self.stdout.write("")
        self.stdout.write("PUBLISHED:")
        for version in published:
            self.stdout.write(
                f"  v{version.version_number} | "
                f"{version.name} | "
                f"ENTRIES={version.entries.count()} | "
                f"CREATED={version.created_at}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 120)
        self.stdout.write("END VERSION / RUN INVENTORY")
        self.stdout.write("=" * 120)
        self.stdout.write("")

    @staticmethod
    def describe_model(model):
        print(f"MODEL: {model._meta.label}")

        for field in model._meta.get_fields():
            relation = getattr(field, "is_relation", False)

            target = ""

            if relation and getattr(field, "remote_field", None):
                remote = getattr(
                    field.remote_field,
                    "model",
                    None,
                )

                if remote is not None:
                    target = (
                        f" -> {getattr(remote._meta, 'label', remote)}"
                    )

            print(
                f"  {field.name} "
                f"(relation={relation})"
                f"{target}"
            )
