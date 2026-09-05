
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.scheduling.models import Period, TimetableEntry, TimetableVersion, SchedulingRun


print("=" * 110)
print("SMARTTIMETABLE PRO - PERIOD 12 / PERIOD 10 ORIGIN + PERSISTENCE TRACE")
print("READ-ONLY: NO DATABASE CHANGES")
print("=" * 110)


# ---------------------------------------------------------------------------
# 1. AUTHORITATIVE PERIOD TABLE
# ---------------------------------------------------------------------------

print()
print("=" * 110)
print("1. ALL DATABASE PERIOD DEFINITIONS")
print("=" * 110)

periods = Period.objects.all().order_by("number", "start_time", "id")

for p in periods:
    print(
        f"ID={p.id} | "
        f"NUMBER={p.number} | "
        f"NAME={p.name!r} | "
        f"START={p.start_time} | "
        f"END={p.end_time}"
    )


# ---------------------------------------------------------------------------
# 2. SPECIFIC PERIOD USED BY THE MONDAY P12 ENTRIES
# ---------------------------------------------------------------------------

print()
print("=" * 110)
print("2. PERIOD OBJECT USED BY MONDAY PERIOD-NUMBER-12 ENTRIES")
print("=" * 110)

p12_ids = list(
    TimetableEntry.objects
    .filter(day="MON", period__number=12)
    .values_list("period_id", flat=True)
    .distinct()
)

print(f"DISTINCT PERIOD IDS: {len(p12_ids)}")

for period_id in p12_ids:
    p = Period.objects.get(id=period_id)

    print()
    print(f"PERIOD ID:     {p.id}")
    print(f"PERIOD NUMBER: {p.number}")
    print(f"PERIOD NAME:   {p.name}")
    print(f"START TIME:    {p.start_time}")
    print(f"END TIME:      {p.end_time}")


# ---------------------------------------------------------------------------
# 3. MONDAY PERIOD 12 ENTRIES
# ---------------------------------------------------------------------------

print()
print("=" * 110)
print("3. ALL MONDAY PERIOD-NUMBER-12 TIMETABLE ENTRIES")
print("=" * 110)

entries = (
    TimetableEntry.objects
    .filter(day="MON", period__number=12)
    .select_related(
        "period",
        "timetable_version",
        "instructional_group",
        "teacher",
        "lesson_requirement",
    )
    .order_by(
        "-timetable_version__version_number",
        "instructional_group__name",
    )
)

print(f"COUNT: {entries.count()}")

for entry in entries:
    p = entry.period
    v = entry.timetable_version

    teacher = entry.teacher
    group = entry.instructional_group
    requirement = entry.lesson_requirement

    print()
    print("-" * 110)
    print(f"ENTRY ID:        {entry.id}")
    print(f"ENTRY CREATED:   {entry.created_at}")
    print(f"VERSION ID:      {v.id}")
    print(f"VERSION NAME:    {v.name}")
    print(f"VERSION NUMBER:  {v.version_number}")
    print(f"VERSION CREATED: {v.created_at}")

    print(f"PERIOD ID:       {p.id}")
    print(f"PERIOD NUMBER:   {p.number}")
    print(f"PERIOD NAME:     {p.name}")
    print(f"PERIOD START:    {p.start_time}")
    print(f"PERIOD END:      {p.end_time}")

    print(f"DAY:             {entry.day}")

    print(
        f"GROUP:           "
        f"{group.id} - {group.name}"
    )

    if teacher is not None:
        print(
            f"TEACHER:         "
            f"{getattr(teacher, 'employee_code', teacher.id)} - "
            f"{getattr(teacher, 'name', str(teacher))}"
        )
    else:
        print("TEACHER:         NONE")

    print(
        f"LESSON REQ:      "
        f"{requirement.id} - "
        f"{getattr(requirement, 'subject_name', getattr(requirement, 'name', str(requirement)))}"
    )


# ---------------------------------------------------------------------------
# 4. DISTINCT VERSIONS
# ---------------------------------------------------------------------------

print()
print("=" * 110)
print("4. DISTINCT TIMETABLE VERSIONS CONTAINING MONDAY PERIOD-NUMBER-12")
print("=" * 110)

versions = (
    TimetableVersion.objects
    .filter(entries__day="MON", entries__period__number=12)
    .distinct()
    .order_by("-version_number")
)

print(f"COUNT: {versions.count()}")

for version in versions:
    print()
    print("-" * 110)
    print(f"VERSION ID:      {version.id}")
    print(f"VERSION NAME:    {version.name}")
    print(f"VERSION NUMBER:  {version.version_number}")
    print(f"VERSION CREATED: {version.created_at}")
    print(f"ACTIVE:          {version.is_active}")
    print(f"PUBLISHED:       {version.is_published}")

    # Correct reverse relation: entries
    entry_count = version.entries.count()

    print(f"TOTAL ENTRIES:   {entry_count}")

    # Correct reverse relation: scheduling_runs
    runs = version.scheduling_runs.all().order_by("-created_at")

    if runs.exists():
        print("ASSOCIATED RUNS:")

        for run in runs:
            print(
                f"  RUN ID={run.id} | "
                f"STATUS={run.status} | "
                f"CREATED={run.created_at} | "
                f"COMPLETED={getattr(run, 'completed_at', None)}"
            )
    else:
        print("ASSOCIATED RUNS: NONE")


# ---------------------------------------------------------------------------
# 5. PERIOD NUMBER / NAME CONSISTENCY CHECK
# ---------------------------------------------------------------------------

print()
print("=" * 110)
print("5. PERIOD NUMBER / NAME CONSISTENCY CHECK")
print("=" * 110)

for p in periods:
    expected_name = f"Period {p.number}"

    if p.name != expected_name:
        print(
            "MISMATCH: "
            f"ID={p.id} | "
            f"NUMBER={p.number} | "
            f"NAME={p.name!r} | "
            f"EXPECTED_NAME={expected_name!r}"
        )


# ---------------------------------------------------------------------------
# 6. DUPLICATE PERIOD-NUMBER CHECK
# ---------------------------------------------------------------------------

print()
print("=" * 110)
print("6. DUPLICATE PERIOD-NUMBER CHECK")
print("=" * 110)

from collections import defaultdict

periods_by_number = defaultdict(list)

for p in periods:
    periods_by_number[p.number].append(p)

duplicates = {
    number: rows
    for number, rows in periods_by_number.items()
    if len(rows) > 1
}

if not duplicates:
    print("NO DUPLICATE PERIOD NUMBERS FOUND.")
else:
    for number, rows in duplicates.items():
        print()
        print(f"DUPLICATE NUMBER: {number}")

        for p in rows:
            print(
                f"  ID={p.id} | "
                f"NAME={p.name!r} | "
                f"START={p.start_time} | "
                f"END={p.end_time}"
            )


# ---------------------------------------------------------------------------
# 7. FINAL DIAGNOSTIC CONCLUSION
# ---------------------------------------------------------------------------

print()
print("=" * 110)
print("7. DIAGNOSTIC CONCLUSION")
print("=" * 110)

p12 = Period.objects.filter(number=12).first()

if p12 is None:
    print("CRITICAL: No database Period with number=12 exists.")
else:
    print(
        f"Database Period #12 -> "
        f"ID={p12.id}, NAME={p12.name!r}, "
        f"START={p12.start_time}, END={p12.end_time}"
    )

    if p12.name != "Period 12":
        print()
        print(
            "IMPORTANT: PERIOD NUMBER 12 DOES NOT HAVE THE EXPECTED NAME "
            "'Period 12'."
        )
        print(
            "The database currently maps the scheduling period number 12 "
            f"to the name {p12.name!r}."
        )

print()
print("=" * 110)
print("END - READ ONLY")
print("=" * 110)
