import django
from collections import Counter, defaultdict

django.setup()

from apps.core.models import Term
from apps.academics.models import LessonRequirement
from apps.scheduling.models import TimetableVersion, TimetableEntry


TERM = Term.objects.get(is_active=True)

VERSION = (
    TimetableVersion.objects
    .filter(term=TERM, version_number=1064)
    .first()
)

if VERSION is None:
    raise RuntimeError("Timetable version 1064 was not found.")

ENTRIES = list(
    TimetableEntry.objects
    .filter(timetable_version=VERSION)
    .select_related(
        "instructional_group",
        "lesson_requirement",
        "lesson_requirement__subject",
        "teacher",
        "period",
    )
)

print("=" * 70)
print("SMARTTIMETABLE PRO - PERSISTED GRADE 10 AUDIT")
print("=" * 70)
print("TERM:", TERM.id, TERM.name)
print("VERSION:", VERSION.id)
print("VERSION NUMBER:", VERSION.version_number)
print("VERSION NAME:", VERSION.name)
print("TOTAL ENTRIES:", len(ENTRIES))
print()

# ------------------------------------------------------------------
# Group identification
# ------------------------------------------------------------------

groups = {}

for entry in ENTRIES:
    group = entry.instructional_group
    code = str(getattr(group, "code", "") or "").strip().upper()
    name = str(getattr(group, "name", "") or "").strip().upper()

    if code in {"10E", "10W"} or name in {
        "10E",
        "10W",
        "GRADE 10E",
        "GRADE 10W",
    }:
        groups[entry.instructional_group_id] = group

print("GRADE 10 GROUPS:", [
    (
        gid,
        getattr(group, "code", None),
        getattr(group, "name", None),
    )
    for gid, group in groups.items()
])

if len(groups) != 2:
    print("WARNING: Expected exactly 2 Grade 10 instructional groups.")

print()

# ------------------------------------------------------------------
# Contract
# ------------------------------------------------------------------

CORE = {
    "ENG": 5,
    "EMCM": 5,
    "KIS": 5,
    "CRE": 4,
    "CSL": 3,
    "ICT": 2,
    "PE": 3,
    "PRP": 1,
    "GST": 1,
}

BLOCKS = {
    "OPTION_1": {"BIO", "MUS", "FRE"},
    "OPTION_2": {"CHEM", "PHY", "LIT"},
    "OPTION_3": {"GEO", "HIS", "CS"},
    "OPTION_4": {"BUS", "AGR", "AGRI"},
}

GROUP_CODES = {}

for gid, group in groups.items():
    GROUP_CODES[gid] = (
        str(getattr(group, "code", "") or getattr(group, "name", "") or gid)
        .strip()
        .upper()
    )

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def subject_code(entry):
    subject = getattr(entry.lesson_requirement, "subject", None)
    return str(getattr(subject, "code", "") or "").strip().upper()


def day_value(entry):
    value = entry.day
    return value.value if hasattr(value, "value") else str(value)


def period_number(entry):
    period = entry.period
    value = getattr(period, "period_number", None)
    if value is not None:
        return int(value)

    value = getattr(period, "number", None)
    if value is not None:
        return int(value)

    return str(period)


# ------------------------------------------------------------------
# Grade 10 entries
# ------------------------------------------------------------------

grade10_entries = [
    e for e in ENTRIES
    if e.instructional_group_id in groups
]

print("GRADE 10 ENTRIES:", len(grade10_entries))
print()

by_group = defaultdict(list)

for entry in grade10_entries:
    by_group[entry.instructional_group_id].append(entry)

# ------------------------------------------------------------------
# Per-group audit
# ------------------------------------------------------------------

all_pass = True

for gid, group in groups.items():

    code = GROUP_CODES[gid]
    entries = by_group[gid]

    print("-" * 70)
    print("GROUP:", code)
    print("ENTRIES:", len(entries))

    # Weekly total
    weekly_total = len(entries)
    weekly_pass = weekly_total == 49

    print(
        "WEEKLY TOTAL:",
        weekly_total,
        "EXPECTED 49:",
        "PASS" if weekly_pass else "FAIL",
    )

    all_pass &= weekly_pass

    # Daily distribution
    daily = Counter(day_value(e) for e in entries)

    print("DAILY DISTRIBUTION:")

    expected_days = {
        "MON": 9,
        "TUE": 10,
        "WED": 10,
        "THU": 10,
        "FRI": 10,
    }

    for day, expected in expected_days.items():
        actual = daily.get(day, 0)
        ok = actual == expected

        print(
            f"  {day}: {actual} / {expected} "
            f"{'PASS' if ok else 'FAIL'}"
        )

        all_pass &= ok

    # Duplicate group slots
    slots = [
        (
            e.instructional_group_id,
            day_value(e),
            period_number(e),
        )
        for e in entries
    ]

    duplicates = [
        slot
        for slot, count in Counter(slots).items()
        if count > 1
    ]

    print(
        "DUPLICATE GROUP SLOTS:",
        len(duplicates),
        "PASS" if not duplicates else "FAIL",
    )

    if duplicates:
        print("  DUPLICATES:", duplicates)

    all_pass &= not duplicates

    # Subject counts
    subject_counts = Counter(subject_code(e) for e in entries)

    print("SUBJECT COUNTS:")

    for subject, count in sorted(subject_counts.items()):
        print(f"  {subject}: {count}")

    print()

    # Core exact counts
    print("CORE REQUIREMENTS:")

    for subject, expected in CORE.items():
        actual = subject_counts.get(subject, 0)
        ok = actual == expected

        print(
            f"  {subject}: {actual} / {expected} "
            f"{'PASS' if ok else 'FAIL'}"
        )

        all_pass &= ok

    print()

    # Option blocks
    print("OPTION BLOCKS:")

    for block, subjects in BLOCKS.items():
        actual = sum(
            subject_counts.get(subject, 0)
            for subject in subjects
        )

        ok = actual == 5

        print(
            f"  {block}: {actual} / 5 "
            f"{'PASS' if ok else 'FAIL'}"
        )

        selected = {
            subject: subject_counts.get(subject, 0)
            for subject in subjects
            if subject_counts.get(subject, 0)
        }

        print("    SELECTED:", selected)

        all_pass &= ok

    print()

    # Option block slot uniqueness
    print("OPTION BLOCK SLOT CHECK:")

    for block, subjects in BLOCKS.items():
        block_entries = [
            e for e in entries
            if subject_code(e) in subjects
        ]

        block_slots = [
            (day_value(e), period_number(e))
            for e in block_entries
        ]

        block_duplicates = [
            slot
            for slot, count in Counter(block_slots).items()
            if count > 1
        ]

        ok = len(block_entries) == 5 and not block_duplicates

        print(
            f"  {block}: "
            f"{len(block_entries)} assignments, "
            f"{len(block_duplicates)} duplicate slots "
            f"{'PASS' if ok else 'FAIL'}"
        )

        if block_duplicates:
            print("    DUPLICATES:", block_duplicates)

        all_pass &= ok

    print()

    # Teacherless entries
    teacherless = [
        e for e in entries
        if e.teacher_id is None
    ]

    print("TEACHERLESS ENTRIES:", len(teacherless))

    for e in teacherless:
        print(
            "  ",
            day_value(e),
            "P" + str(period_number(e)),
            subject_code(e),
            "teacher=None",
        )

    print()

# ------------------------------------------------------------------
# Teacher audit
# ------------------------------------------------------------------

print("=" * 70)
print("TEACHER AUDIT")
print("=" * 70)

teacher_entries = [
    e for e in grade10_entries
    if e.teacher_id is not None
]

teacher_slot_counts = Counter()

for e in teacher_entries:
    teacher_slot_counts[
        (
            e.teacher_id,
            day_value(e),
            period_number(e),
        )
    ] += 1

teacher_duplicates = [
    slot
    for slot, count in teacher_slot_counts.items()
    if count > 1
]

print("TEACHER ASSIGNED ENTRIES:", len(teacher_entries))
print(
    "TEACHER CLASHES:",
    len(teacher_duplicates),
    "PASS" if not teacher_duplicates else "FAIL",
)

if teacher_duplicates:
    for item in teacher_duplicates:
        print("  ", item)

all_pass &= not teacher_duplicates

print()

# ------------------------------------------------------------------
# Assembly / Monday P1
# ------------------------------------------------------------------

print("=" * 70)
print("MONDAY P1 / ASSEMBLY AUDIT")
print("=" * 70)

for gid, group in groups.items():
    entries = by_group[gid]

    p1 = [
        e for e in entries
        if day_value(e) == "MON" and period_number(e) == 1
    ]

    print(
        GROUP_CODES[gid],
        "Monday P1 entries:",
        len(p1),
    )

    for e in p1:
        print(
            "  ",
            subject_code(e),
            getattr(e.lesson_requirement, "subject_id", None),
        )

print()

# ------------------------------------------------------------------
# Final summary
# ------------------------------------------------------------------

print("=" * 70)
print("FINAL AUDIT RESULT")
print("=" * 70)

print(
    "GRADE 10 CONTRACT AUDIT:",
    "PASS" if all_pass else "FAIL",
)

print("PERSISTED VERSION:", VERSION.version_number)
print("PERSISTED ENTRIES:", len(ENTRIES))

if not all_pass:
    raise SystemExit(2)