from collections import Counter, defaultdict

from apps.scheduling.models import SchedulingRun, LessonRequirement


RUN_ID = "64a045ae-6bfd-464e-9775-304fdc9287e3"

run = (
    SchedulingRun.objects
    .select_related("term", "timetable_version")
    .get(id=RUN_ID)
)

version = run.timetable_version

entries = list(
    version.entries
    .select_related(
        "instructional_group",
        "instructional_group__teaching_group",
        "lesson_requirement",
        "lesson_requirement__subject",
        "teacher",
        "room",
        "period",
    )
    .all()
)

print("=" * 82)
print("SMARTTIMETABLE PRO - GRADE 10 FULL BUSINESS-RULE AUDIT")
print("=" * 82)
print("RUN:", run.id)
print("VERSION:", version.id)
print("STATUS:", run.status)
print("SOLVER:", run.solver_status)
print("OBJECTIVE:", run.objective_value)
print("TOTAL ENTRIES:", len(entries))
print()

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def group_name(entry):
    return str(entry.instructional_group.teaching_group)


def subject_name(entry):
    requirement = entry.lesson_requirement
    subject = requirement.subject

    return (
        getattr(subject, "code", None)
        or getattr(subject, "name", None)
        or str(subject)
    )


def period_number(entry):
    return getattr(entry.period, "number", None)


# ---------------------------------------------------------------------
# 1. TOTAL / GROUP COUNTS
# ---------------------------------------------------------------------
print("=== 1. WEEKLY LESSON COUNTS ===")

groups = defaultdict(list)

for entry in entries:
    groups[group_name(entry)].append(entry)

group_failures = []

for name, group_entries in sorted(groups.items()):
    count = len(group_entries)
    result = "PASS" if count == 49 else "FAIL"

    print(f"{name}: {count} / 49 -> {result}")

    if count != 49:
        group_failures.append((name, count))

print()

# ---------------------------------------------------------------------
# 2. DAY DISTRIBUTION
# ---------------------------------------------------------------------
print("=== 2. DAY DISTRIBUTION ===")

expected_days = {
    "MON": 9,
    "TUE": 10,
    "WED": 10,
    "THU": 10,
    "FRI": 10,
}

day_failures = []

for name, group_entries in sorted(groups.items()):
    counts = Counter(entry.day for entry in group_entries)

    print(name)

    for day, expected in expected_days.items():
        actual = counts.get(day, 0)
        result = "PASS" if actual == expected else "FAIL"

        print(f"  {day}: {actual} / {expected} -> {result}")

        if actual != expected:
            day_failures.append((name, day, actual, expected))

print()

# ---------------------------------------------------------------------
# 3. MONDAY P1 ASSEMBLY
# ---------------------------------------------------------------------
print("=== 3. MONDAY P1 ASSEMBLY ===")

monday_p1 = [
    entry
    for entry in entries
    if entry.day == "MON" and period_number(entry) == 1
]

print("MON P1 persisted teaching entries:", len(monday_p1))

if monday_p1:
    print("FAIL: teaching entries exist at Monday P1.")

    for entry in monday_p1:
        print(
            " ",
            group_name(entry),
            subject_name(entry),
            "teacher=",
            entry.teacher,
        )
else:
    print("PASS: Monday P1 has no teaching entry.")

print()

# ---------------------------------------------------------------------
# 4. GROUP DAY/PERIOD COLLISIONS
# ---------------------------------------------------------------------
print("=== 4. GROUP DAY/PERIOD COLLISIONS ===")

group_cells = defaultdict(list)

for entry in entries:
    key = (
        group_name(entry),
        entry.day,
        period_number(entry),
    )
    group_cells[key].append(entry)

group_collisions = {
    key: values
    for key, values in group_cells.items()
    if len(values) > 1
}

print("Duplicate group/day/period cells:", len(group_collisions))

if group_collisions:
    print("FAIL")

    for key, values in sorted(group_collisions.items()):
        print(" ", key, "=", len(values))
else:
    print("PASS: no duplicate group/day/period cells.")

print()

# ---------------------------------------------------------------------
# 5. SUBJECT DISTRIBUTION
# ---------------------------------------------------------------------
print("=== 5. SUBJECT DISTRIBUTION ===")

for name, group_entries in sorted(groups.items()):
    counts = Counter(subject_name(entry) for entry in group_entries)

    print(name)

    for subject, count in sorted(counts.items()):
        print(f"  {subject}: {count}")

print()

# ---------------------------------------------------------------------
# 6. GRADE 10 ELECTIVE BLOCKS
# ---------------------------------------------------------------------
print("=== 6. GRADE 10 ELECTIVE BLOCK AUDIT ===")

blocks = {
    "OPTION 1": {"BIO", "MUS", "FRE"},
    "OPTION 2": {"CHEM", "PHY", "LIT"},
    "OPTION 3": {"GEO", "HIST", "GOV", "CS"},
    "OPTION 4": {"BUS", "AGRI"},
}

block_failures = []

for name, group_entries in sorted(groups.items()):
    counts = Counter(
        subject_name(entry).upper()
        for entry in group_entries
    )

    print(name)

    for block, subjects in blocks.items():
        total = sum(
            count
            for subject, count in counts.items()
            if subject in subjects
        )

        result = "PASS" if total == 5 else "CHECK"

        print(f"  {block}: {total} / 5 -> {result}")

        if total != 5:
            block_failures.append((name, block, total))

print()

# ---------------------------------------------------------------------
# 7. TEACHER COLLISIONS
# ---------------------------------------------------------------------
print("=== 7. TEACHER COLLISION AUDIT ===")

teacher_cells = defaultdict(list)

for entry in entries:
    teacher = entry.teacher

    if teacher is None:
        continue

    teacher_id = teacher.pk

    key = (
        teacher_id,
        entry.day,
        period_number(entry),
    )

    teacher_cells[key].append(entry)

teacher_collisions = {
    key: values
    for key, values in teacher_cells.items()
    if len(values) > 1
}

print("Teacher collision cells:", len(teacher_collisions))

if teacher_collisions:
    print("FAIL")

    for key, values in sorted(
        teacher_collisions.items(),
        key=lambda item: str(item[0]),
    ):
        teacher = values[0].teacher

        print(
            " ",
            key,
            "teacher=",
            teacher,
            "entries=",
            len(values),
        )

        for entry in values:
            print(
                "    ",
                group_name(entry),
                subject_name(entry),
            )
else:
    print("PASS: no teacher collisions.")

print()

# ---------------------------------------------------------------------
# 8. ROOM COLLISIONS
# ---------------------------------------------------------------------
print("=== 8. ROOM COLLISION AUDIT ===")

room_cells = defaultdict(list)

for entry in entries:
    room = entry.room

    if room is None:
        continue

    key = (
        room.pk,
        entry.day,
        period_number(entry),
    )

    room_cells[key].append(entry)

room_collisions = {
    key: values
    for key, values in room_cells.items()
    if len(values) > 1
}

print("Room collision cells:", len(room_collisions))

if room_collisions:
    print("FAIL")

    for key, values in sorted(
        room_collisions.items(),
        key=lambda item: str(item[0]),
    ):
        print(
            " ",
            key,
            "room=",
            values[0].room,
            "entries=",
            len(values),
        )
else:
    print("PASS: no room collisions.")

print()

# ---------------------------------------------------------------------
# 9. LESSON REQUIREMENT COUNTS
# ---------------------------------------------------------------------
print("=== 9. LESSON REQUIREMENT VS PERSISTED COUNTS ===")

requirement_fields = {
    field.name
    for field in LessonRequirement._meta.get_fields()
}

print("LessonRequirement fields:")
print(" ", ", ".join(sorted(requirement_fields)))

frequency_candidates = (
    "lessons_per_week",
    "periods_per_week",
    "weekly_lessons",
    "weekly_periods",
    "frequency",
)

frequency_field = next(
    (
        name
        for name in frequency_candidates
        if name in requirement_fields
    ),
    None,
)

print("Detected weekly-frequency field:", frequency_field)

requirements = list(
    LessonRequirement.objects
    .filter(
        term=run.term,
        is_active=True,
        instructional_group_id__in={
            entry.instructional_group_id
            for entry in entries
        },
    )
    .select_related(
        "instructional_group",
        "subject",
    )
)

print("Active requirements:", len(requirements))

actual_requirement_counts = Counter(
    (
        entry.instructional_group_id,
        entry.lesson_requirement_id,
    )
    for entry in entries
)

# Use lesson_requirement_id rather than subject_id so multiple
# requirements for the same subject cannot be accidentally merged.
requirement_failures = []

if frequency_field is None:
    print(
        "CHECK: weekly-frequency field was not identified automatically."
    )
else:
    for requirement in requirements:
        expected = getattr(requirement, frequency_field)

        actual = actual_requirement_counts.get(
            (
                requirement.instructional_group_id,
                requirement.pk,
            ),
            0,
        )

        if actual != expected:
            requirement_failures.append(
                (
                    requirement.pk,
                    requirement.instructional_group_id,
                    requirement.subject,
                    expected,
                    actual,
                )
            )

    print(
        "Requirement count mismatches:",
        len(requirement_failures),
    )

    if requirement_failures:
        print("FAIL/CHECK")

        for failure in requirement_failures:
            print(" ", failure)
    else:
        print(
            "PASS: persisted counts match every active "
            "LessonRequirement."
        )

print()

# ---------------------------------------------------------------------
# 10. NULL TEACHERS / ROOMS
# ---------------------------------------------------------------------
print("=== 10. MISSING RESOURCE ASSIGNMENTS ===")

null_teachers = [
    entry
    for entry in entries
    if entry.teacher_id is None
]

null_rooms = [
    entry
    for entry in entries
    if entry.room_id is None
]

print("Entries without teacher:", len(null_teachers))
print("Entries without room:", len(null_rooms))

if null_teachers:
    print("CHECK: teacher assignments are missing.")

if null_rooms:
    print("CHECK: room assignments are missing.")

if not null_teachers:
    print("PASS: every entry has a teacher.")

if not null_rooms:
    print("PASS: every entry has a room.")

print()

# ---------------------------------------------------------------------
# FINAL SUMMARY
# ---------------------------------------------------------------------
print("=" * 82)
print("FINAL AUDIT SUMMARY")
print("=" * 82)

checks = [
    ("98 total persisted entries", len(entries) == 98),
    ("Grade 10 groups have 49 each", not group_failures),
    ("Daily distribution", not day_failures),
    ("Monday P1 has no teaching", not monday_p1),
    ("No group collisions", not group_collisions),
    ("Elective blocks", not block_failures),
    ("No teacher collisions", not teacher_collisions),
    ("No room collisions", not room_collisions),
    (
        "Lesson requirements",
        frequency_field is None or not requirement_failures,
    ),
    ("Every entry has teacher", not null_teachers),
    ("Every entry has room", not null_rooms),
]

failed = []

for label, passed in checks:
    print(f"{'PASS' if passed else 'FAIL'}: {label}")

    if not passed:
        failed.append(label)

print()

if failed:
    print("OVERALL RESULT: FAIL/CHECK")
    print("Items requiring investigation:")
    for item in failed:
        print(" -", item)
else:
    print("OVERALL RESULT: PASS")
    print("All automated checks completed successfully.")

print("=" * 82)