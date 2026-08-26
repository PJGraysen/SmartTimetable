from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.core.models import Term
from apps.scheduling.models import (
    Teacher,
    TeacherAvailability,
    TimetableEntry,
)


class Command(BaseCommand):
    help = (
        "Analyze existing timetable entries to determine the afternoon "
        "free-day pattern for teachers T001-T020."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            "\n=== TEACHER AFTERNOON AVAILABILITY ANALYSIS ===\n"
        )

        term = (
            Term.objects
            .order_by("-start_date", "name")
            .first()
        )

        if term is None:
            self.stdout.write(
                self.style.ERROR("No academic term exists.")
            )
            return

        self.stdout.write(
            f"Term: {term.pk} | {term.name}\n"
        )

        teachers = list(
            Teacher.objects
            .all()
            .order_by("teacher_number")
        )

        # ------------------------------------------------------------
        # Inspect TeacherAvailability first.
        # ------------------------------------------------------------
        self.stdout.write(
            "\n=== EXISTING TEACHER AVAILABILITY ==="
        )

        for teacher in teachers:
            records = list(
                TeacherAvailability.objects
                .filter(
                    teacher=teacher,
                    term=term,
                )
                .order_by("day", "period")
            )

            self.stdout.write(
                f"\n{teacher.employee_code}: "
                f"{len(records)} availability record(s)"
            )

            for record in records:
                values = []

                for field in record._meta.fields:
                    if field.name in {"id", "created_at", "updated_at"}:
                        continue

                    try:
                        value = getattr(record, field.name)

                        if hasattr(value, "employee_code"):
                            value = value.employee_code

                        if hasattr(value, "name"):
                            value = value.name

                        values.append(
                            f"{field.name}={value}"
                        )
                    except Exception:
                        values.append(
                            f"{field.name}=<unavailable>"
                        )

                self.stdout.write(
                    "  " + " | ".join(values)
                )

        # ------------------------------------------------------------
        # Inspect existing timetable entries.
        # ------------------------------------------------------------
        self.stdout.write(
            "\n\n=== EXISTING TIMETABLE ENTRIES ==="
        )

        entries = (
            TimetableEntry.objects
            .select_related(
                "teacher",
                "period",
            )
            .filter(
                teacher__isnull=False,
            )
            .order_by(
                "teacher__teacher_number",
                "period__day",
                "period__start_time",
            )
        )

        teacher_days = defaultdict(
            lambda: defaultdict(list)
        )

        for entry in entries:
            teacher = entry.teacher

            if teacher is None:
                continue

            period = entry.period

            day = getattr(
                period,
                "day",
                None,
            )

            start_time = getattr(
                period,
                "start_time",
                None,
            )

            end_time = getattr(
                period,
                "end_time",
                None,
            )

            teacher_days[
                teacher.employee_code
            ][str(day)].append(
                (
                    start_time,
                    end_time,
                )
            )

        # ------------------------------------------------------------
        # Determine whether afternoon usage can identify a free day.
        # ------------------------------------------------------------
        afternoon_start = "13:00"

        self.stdout.write(
            "\n\n=== TEACHER DAY-BY-DAY AFTERNOON USAGE ==="
        )

        days = ["MON", "TUE", "WED", "THU", "FRI"]

        for teacher in teachers:
            code = teacher.employee_code

            self.stdout.write(
                f"\n{code}"
            )

            for day in days:
                periods = teacher_days[code].get(day, [])

                afternoon_periods = [
                    item
                    for item in periods
                    if item[0] is not None
                    and str(item[0]) >= afternoon_start
                ]

                if afternoon_periods:
                    self.stdout.write(
                        f"  {day}: AFTERNOON TEACHING "
                        f"({len(afternoon_periods)} period(s))"
                    )
                else:
                    self.stdout.write(
                        f"  {day}: NO RECORDED AFTERNOON TEACHING"
                    )

        self.stdout.write(
            "\n=== ANALYSIS COMPLETE: NO DATABASE CHANGES ==="
        )
