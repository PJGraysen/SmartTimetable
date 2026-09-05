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


def group_label(group):
    code = str(getattr(group, "code", "") or "").strip()
    name = str(getattr(group, "name", "") or "").strip()

    return code or name or str(group.id)


def subject_code(entry):
    subject = getattr(entry.lesson_requirement, "subject", None)

    return str(
        getattr(subject, "code", "") or ""
    ).strip().upper()


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


# ==============================================================
# AUTHORITATIVE CONTRACT
# ==============================================================

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

EXPECTED_DAILY = {
    "MON": 9,
    "TUE": 10,
    "WED": 10,
    "THU": 10,
    "FRI": 10,
}


# ==============================================================
# HEADER
# ==============================================================

print("=" * 72)
print("SMARTTIMETABLE PRO - PERSISTED GRADE 10 AUDIT")
print("=" * 72)

print("TERM:", TERM.id)
print("TERM NAME:", TERM.name)
print("VERSION ID:", VERSION.id)
print("VERSION NUMBER:", VERSION.version_number)
print("VERSION NAME:", VERSION.name)
print("TOTAL PERSISTED ENTRIES:", len(ENTRIES))
print()


# ==============================================================
# FIND GRADE 10 GROUPS
# ==============================================================

grade10_groups = {}

for entry in ENTRIES:
    group = entry.instructional_group

    code = str(
        getattr(group, "code", "") or ""
    ).strip().upper()

    name = str(
        getattr(group, "name", "") or ""
    ).strip().upper()

    if code in {"10E", "10W"} or name in {
        "10E",
        "10W",
        "GRADE 10E",
        "GRADE 10W",
    }:
        grade10_groups[entry.instructional_group_id] = group


print("GRADE 10 GROUPS:", len(grade10_groups))

for group_id, group in grade10_groups.items():
    print(
        "  ",
        group_id,
        group_label(group),
    )

print()


if len(grade10_groups) != 2:
    raise RuntimeError(
        "Expected exactly two Grade 10 instructional groups."
    )


grade10_entries = [
    entry
    for entry in ENTRIES
    if entry.instructional_group_id in grade10_groups
]


print("GRADE 10 PERSISTED ENTRIES:", len(grade10_entries))
print()


# ==============================================================
# PER-GROUP AUDIT
# ==============================================================

overall_pass = True

entries_by_group = defaultdict(list)

for entry in grade10_entries:
    entries_by_group[
        entry.instructional_group_id
    ].append(entry)


for group_id, group in grade10_groups.items():

    label = group_label(group)
    entries = entries_by_group[group_id]

    print("=" * 72)
    print("GROUP:", label)
    print("=" * 72)

    # ----------------------------------------------------------
    # Weekly total
    # ----------------------------------------------------------

    weekly_total = len(entries)
    ok = weekly_total == 49

    print(
        "WEEKLY TOTAL:",
        weekly_total,
        "/ 49",
        "PASS" if ok else "FAIL",
    )

    overall_pass &= ok

    # ----------------------------------------------------------
    # Daily distribution
    # ----------------------------------------------------------

    daily = Counter(
        day_value(entry)
        for entry in entries
    )

    print("DAILY DISTRIBUTION:")

    for day, expected in EXPECTED_DAILY.items():

        actual = daily.get(day, 0)
        ok = actual == expected

        print(
            "  ",
            day,
            ":",
            actual,
            "/",
            expected,
            "PASS" if ok else "FAIL",
        )

        overall_pass &= ok

    # ----------------------------------------------------------
    # Duplicate instructional-group slots
    # ----------------------------------------------------------

    slots = [
        (
            day_value(entry),
            period_number(entry),
        )
        for entry in entries
    ]

    slot_counts = Counter(slots)

    duplicates = [
        slot
        for slot, count in slot_counts.items()
        if count > 1
    ]

    ok = not duplicates

    print(
        "DUPLICATE GROUP SLOTS:",
        len(duplicates),
        "PASS" if ok else "FAIL",
    )

    if duplicates:
        for slot in duplicates:
            print("  ", slot)

    overall_pass &= ok

    # ----------------------------------------------------------
    # Subject counts
    # ----------------------------------------------------------

    subject_counts = Counter(
        subject_code(entry)
        for entry in entries
    )

    print()
    print("SUBJECT COUNTS:")

    for subject, count in sorted(subject_counts.items()):
        print(
            "  ",
            subject,
            ":",
            count,
        )

    # ----------------------------------------------------------
    # Core requirements
    # ----------------------------------------------------------

    print()
    print("CORE REQUIREMENTS:")

    for subject, expected in CORE.items():

        actual = subject_counts.get(subject, 0)
        ok = actual == expected

        print(
            "  ",
            subject,
            ":",
            actual,
            "/",
            expected,
            "PASS" if ok else "FAIL",
        )

        overall_pass &= ok

    # ----------------------------------------------------------
    # Shared option blocks
    # ----------------------------------------------------------

    print()
    print("OPTION BLOCKS:")

    for block_name, subjects in BLOCKS.items():

        block_entries = [
            entry
            for entry in entries
            if subject_code(entry) in subjects
        ]

        actual = len(block_entries)
        ok = actual == 5

        print(
            "  ",
            block_name,
            ":",
            actual,
            "/ 5",
            "PASS" if ok else "FAIL",
        )

        selected = Counter(
            subject_code(entry)
            for entry in block_entries
        )

        print(
            "      SELECTED:",
            dict(sorted(selected.items())),
        )

        overall_pass &= ok

        # ------------------------------------------------------
        # Each shared block must occupy five distinct slots.
        # ------------------------------------------------------

        block_slots = [
            (
                day_value(entry),
                period_number(entry),
            )
            for entry in block_entries
        ]

        block_slot_counts = Counter(block_slots)

        block_duplicates = [
            slot
            for slot, count in block_slot_counts.items()
            if count > 1
        ]

        block_slot_ok = (
            len(block_entries) == 5
            and not block_duplicates
        )

        print(
            "      SHARED SLOT UNIQUENESS:",
            "PASS" if block_slot_ok else "FAIL",
        )

        if block_duplicates:
            for slot in block_duplicates:
                print("        DUPLICATE:", slot)

        overall_pass &= block_slot_ok

    # ----------------------------------------------------------
    # Teacherless assignments
    # ----------------------------------------------------------

    teacherless = [
        entry
        for entry in entries
        if entry.teacher_id is None
    ]

    print()
    print(
        "TEACHERLESS ENTRIES:",
        len(teacherless),
    )

    for entry in teacherless:
        print(
            "  ",
            day_value(entry),
            "P" + str(period_number(entry)),
            subject_code(entry),
            "teacher=None",
        )

    # ----------------------------------------------------------
    # Full placement listing
    # ----------------------------------------------------------

    print()
    print("PLACEMENTS:")

    for entry in sorted(
        entries,
        key=lambda item: (
            day_value(item),
            period_number(item),
            subject_code(item),
        ),
    ):
        teacher = entry.teacher

        teacher_label = (
            "NONE"
            if teacher is None
            else str(
                getattr(teacher, "employee_number", "")
                or getattr(teacher, "name", "")
                or teacher.id
            )
        )

        print(
            "  ",
            day_value(entry),
            "P" + str(period_number(entry)),
            subject_code(entry),
            "TEACHER=" + teacher_label,
        )

    print()


# ==============================================================
# TEACHER CLASH AUDIT
# ==============================================================

print("=" * 72)
print("TEACHER CLASH AUDIT")
print("=" * 72)

teacher_slots = Counter()

for entry in grade10_entries:

    if entry.teacher_id is None:
        continue

    teacher_slots[
        (
            entry.teacher_id,
            day_value(entry),
            period_number(entry),
        )
    ] += 1


teacher_clashes = [
    slot
    for slot, count in teacher_slots.items()
    if count > 1
]


print(
    "TEACHER CLASHES:",
    len(teacher_clashes),
    "PASS" if not teacher_clashes else "FAIL",
)

if teacher_clashes:
    for clash in teacher_clashes:
        print("  ", clash)

overall_pass &= not teacher_clashes

print()


# ==============================================================
# MONDAY P1 AUDIT
# ==============================================================

print("=" * 72)
print("MONDAY P1 / ASSEMBLY AUDIT")
print("=" * 72)

for group_id, group in grade10_groups.items():

    entries = entries_by_group[group_id]

    monday_p1 = [
        entry
        for entry in entries
        if day_value(entry) == "MON"
        and period_number(entry) == 1
    ]

    print(
        group_label(group),
        "Monday P1 entries:",
        len(monday_p1),
    )

    for entry in monday_p1:
        print(
            "  ",
            subject_code(entry),
        )

print()


# ==============================================================
# FINAL RESULT
# ==============================================================

print("=" * 72)
print("FINAL AUDIT RESULT")
print("=" * 72)

print(
    "GRADE 10 CONTRACT:",
    "PASS" if overall_pass else "FAIL",
)

print(
    "PERSISTED VERSION:",
    VERSION.version_number,
)

print(
    "TOTAL DATABASE ENTRIES:",
    len(ENTRIES),
)

print(
    "GRADE 10 ENTRIES:",
    len(grade10_entries),
)

if not overall_pass:
    raise SystemExit(2)

print()
print("READ-ONLY AUDIT COMPLETE: PASS")