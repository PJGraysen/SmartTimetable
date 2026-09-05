from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.scheduling.models import (
    LessonRequirement,
    TimetableEntry,
    TeacherFreeAfternoon,
    SchedulingRun,
)


GROUPS = ("10E", "10W")

DAY_EXPECTED = {
    "MON": 9,
    "TUE": 10,
    "WED": 10,
    "THU": 10,
    "FRI": 10,
}

CORE_REQUIREMENTS = {
    "ENG": 5,
    "KIS": 5,
    "EMCM": 5,
    "CRE": 4,
    "PE": 3,
    "CSL": 3,
    "ICT": 2,
    "PRP": 1,
}

ELECTIVE_BLOCKS = {
    "OPTION 1": ("BIO", "MUS", "FRE"),
    "OPTION 2": ("CHEM", "PHY", "LIT"),
    "OPTION 3": ("GEO", "HIST", "GOV", "CS"),
    "OPTION 4": ("BUS", "AGR"),
}

ALLOWED_TEACHERLESS = {"FRE", "GST", "LF"}

NON_TEACHING_PERIODS = {13, 14}
AFTERNOON_PERIODS = {10, 11, 12}


def subject_code(subject):
    value = getattr(subject, "code", None) or getattr(subject, "name", "")
    value = str(value).strip().upper()

    aliases = {
        "AGRI": "AGR",
        "HISTORY": "HIST",
        "ESSENTIAL/CORE MATHEMATICS": "EMCM",
        "ESSENTIAL MATHEMATICS": "EMCM",
        "CORE MATHEMATICS": "EMCM",
    }

    return aliases.get(value, value)


def group_code(obj):
    ig = obj.instructional_group
    tg = ig.teaching_group

    values = (
        getattr(ig, "code", ""),
        getattr(ig, "name", ""),
        getattr(tg, "code", ""),
        getattr(tg, "name", ""),
    )

    text = " ".join(str(v).upper() for v in values if v)

    if "10E" in text:
        return "10E"
    if "10W" in text:
        return "10W"

    return None


def day_code(entry):
    return str(getattr(entry, "day", "") or "").upper().strip()


def cell(entry):
    return (day_code(entry), entry.period.number)


def is_grade10_group(code):
    return code in GROUPS


def is_teaching_entry(entry):
    day = day_code(entry)
    period = entry.period.number

    if day not in DAY_EXPECTED:
        return False

    if period in NON_TEACHING_PERIODS:
        return False

    if day == "MON" and period == 1:
        return False

    return True


class Command(BaseCommand):
    help = "Read-only authoritative Grade 10 business-contract audit."

    def handle(self, *args, **options):
        self.stdout.write("=" * 100)
        self.stdout.write(
            "SMARTTIMETABLE PRO — GRADE 10 AUTHORITATIVE BUSINESS CONTRACT AUDIT"
        )
        self.stdout.write("=" * 100)

        run = (
            SchedulingRun.objects
            .filter(status="COMPLETED")
            .select_related("term", "timetable_version")
            .order_by("-completed_at")
            .first()
        )

        if run is None:
            self.stdout.write(self.style.ERROR(
                "FAIL: No completed scheduling run exists."
            ))
            return

        entries = list(
            TimetableEntry.objects
            .filter(timetable_version=run.timetable_version)
            .select_related(
                "period",
                "instructional_group",
                "instructional_group__teaching_group",
                "lesson_requirement",
                "lesson_requirement__subject",
                "teacher",
                "room",
            )
        )

        requirements = list(
            LessonRequirement.objects
            .filter(
                term=run.term,
                is_active=True,
            )
            .select_related(
                "instructional_group",
                "instructional_group__teaching_group",
                "subject",
            )
        )

        overall_pass = True

        group_entries = defaultdict(list)
        group_requirements = defaultdict(list)

        for entry in entries:
            group = group_code(entry)
            if is_grade10_group(group):
                group_entries[group].append(entry)

        for requirement in requirements:
            group = group_code(requirement)
            if is_grade10_group(group):
                group_requirements[group].append(requirement)

        self.stdout.write(f"RUN:             {run.id}")
        self.stdout.write(f"VERSION:         {run.timetable_version_id}")
        self.stdout.write(f"TOTAL ENTRIES:   {len(entries)}")
        self.stdout.write(f"REQUIREMENTS:    {len(requirements)}")
        self.stdout.write("")

        # ------------------------------------------------------------
        # GROUP / 49-LESSON / NON-TEACHING AUDIT
        # ------------------------------------------------------------

        for group in GROUPS:
            self.stdout.write("-" * 100)
            self.stdout.write(f"GRADE 10{group[-1]}")
            self.stdout.write("-" * 100)

            ge = group_entries[group]
            teaching = [e for e in ge if is_teaching_entry(e)]

            cells = [cell(e) for e in teaching]
            unique_cells = set(cells)

            self.stdout.write(
                f"TEACHING CELLS: {len(unique_cells)}/49 "
                f"{'PASS' if len(unique_cells) == 49 else 'FAIL'}"
            )

            if len(unique_cells) != 49:
                overall_pass = False

            for day, expected in DAY_EXPECTED.items():
                actual = len({
                    c for c in unique_cells if c[0] == day
                })

                ok = actual == expected

                self.stdout.write(
                    f"  {day}: {actual}/{expected} "
                    f"{'PASS' if ok else 'FAIL'}"
                )

                if not ok:
                    overall_pass = False

            forbidden = [
                e for e in ge
                if (
                    (day_code(e) == "MON" and e.period.number == 1)
                    or e.period.number in NON_TEACHING_PERIODS
                )
            ]

            ok = not forbidden

            self.stdout.write(
                f"ASSEMBLY/P13/P14 TEACHING: "
                f"{len(forbidden)} "
                f"{'PASS' if ok else 'FAIL'}"
            )

            if not ok:
                overall_pass = False

            # --------------------------------------------------------
            # SUBJECT COUNTS
            # --------------------------------------------------------

            subject_cells = defaultdict(set)
            subject_entries = defaultdict(list)

            for entry in teaching:
                code = subject_code(
                    entry.lesson_requirement.subject
                )
                subject_cells[code].add(cell(entry))
                subject_entries[code].append(entry)

            self.stdout.write("")
            self.stdout.write("CORE / STANDALONE")

            for code, expected in CORE_REQUIREMENTS.items():
                actual = len(subject_cells[code])
                ok = actual == expected

                self.stdout.write(
                    f"  {code:<6} {actual}/{expected} "
                    f"{'PASS' if ok else 'FAIL'}"
                )

                if not ok:
                    overall_pass = False

            # --------------------------------------------------------
            # GROUP STUDY / LF
            # --------------------------------------------------------

            gst_cells = set()

            for code in ("GST", "LF"):
                gst_cells.update(subject_cells[code])

            ok = len(gst_cells) == 1

            self.stdout.write(
                f"  GST/LF {len(gst_cells)}/1 "
                f"{'PASS' if ok else 'FAIL'}"
            )

            if not ok:
                overall_pass = False

            # --------------------------------------------------------
            # ELECTIVE BLOCKS
            # --------------------------------------------------------

            self.stdout.write("")
            self.stdout.write("ELECTIVE BLOCKS")

            for block, subjects in ELECTIVE_BLOCKS.items():
                block_ok = True
                block_cells = {}

                self.stdout.write(f"  {block}")

                for code in subjects:
                    actual = len(subject_cells[code])
                    expected = 5
                    ok = actual == expected

                    self.stdout.write(
                        f"    {code:<6} {actual}/{expected} "
                        f"{'PASS' if ok else 'FAIL'}"
                    )

                    block_cells[code] = subject_cells[code]

                    if not ok:
                        block_ok = False
                        overall_pass = False

                # All subjects in the block MUST occupy
                # exactly the same five day/period cells.
                if all(block_cells.values()):
                    common = set.intersection(
                        *block_cells.values()
                    )

                    union = set.union(
                        *block_cells.values()
                    )

                    synchronized = (
                        len(common) == 5
                        and len(union) == 5
                        and all(
                            cells == common
                            for cells in block_cells.values()
                        )
                    )
                else:
                    synchronized = False
                    common = set()

                self.stdout.write(
                    f"    SYNCHRONIZED: {len(common)}/5 "
                    f"{'PASS' if synchronized else 'FAIL'}"
                )

                if not synchronized:
                    block_ok = False
                    overall_pass = False

                    for code, cells in block_cells.items():
                        self.stdout.write(
                            f"      {code}: "
                            + ", ".join(
                                f"{d}/P{p}"
                                for d, p in sorted(cells)
                            )
                        )

                self.stdout.write(
                    f"    {block} RESULT: "
                    f"{'PASS' if block_ok else 'FAIL'}"
                )

            # --------------------------------------------------------
            # TEACHERLESS RULE
            # --------------------------------------------------------

            teacherless = [
                e for e in teaching
                if e.teacher_id is None
            ]

            unexpected = [
                e for e in teacherless
                if subject_code(e.lesson_requirement.subject)
                not in ALLOWED_TEACHERLESS
            ]

            ok = not unexpected

            self.stdout.write("")
            self.stdout.write(
                f"TEACHERLESS ENTRIES: {len(teacherless)}"
            )
            self.stdout.write(
                f"UNEXPECTED TEACHERLESS: {len(unexpected)} "
                f"{'PASS' if ok else 'FAIL'}"
            )

            if not ok:
                overall_pass = False

        # ------------------------------------------------------------
        # TEACHER COLLISIONS
        # ------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write("TEACHER COLLISION AUDIT")
        self.stdout.write("=" * 100)

        teacher_cells = defaultdict(list)

        for entry in entries:
            if not is_teaching_entry(entry):
                continue

            if entry.teacher_id is None:
                continue

            teacher_cells[
                (entry.teacher_id, cell(entry))
            ].append(entry)

        collisions = {
            key: values
            for key, values in teacher_cells.items()
            if len(values) > 1
        }

        ok = not collisions

        self.stdout.write(
            f"TEACHER COLLISIONS: {len(collisions)} "
            f"{'PASS' if ok else 'FAIL'}"
        )

        if not ok:
            overall_pass = False

            for (teacher_id, c), values in collisions.items():
                subjects = ", ".join(
                    subject_code(
                        e.lesson_requirement.subject
                    )
                    for e in values
                )

                self.stdout.write(
                    f"  Teacher {teacher_id} {c}: {subjects}"
                )

        # ------------------------------------------------------------
        # FREE AFTERNOON AUDIT
        # ------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write("TEACHER FREE-AFTERNOON AUDIT")
        self.stdout.write("=" * 100)

        model_fields = {
            field.name
            for field in TeacherFreeAfternoon._meta.get_fields()
            if getattr(field, "concrete", False)
        }

        teacher_field = "teacher" if "teacher" in model_fields else None

        day_field = next(
            (
                name
                for name in (
                    "day",
                    "day_of_week",
                    "weekday",
                )
                if name in model_fields
            ),
            None,
        )

        if teacher_field is None or day_field is None:
            self.stdout.write(self.style.ERROR(
                "FREE-AFTERNOON AUDIT: FAIL — "
                "TeacherFreeAfternoon day/teacher fields unavailable."
            ))
            self.stdout.write(
                f"AVAILABLE FIELDS: {sorted(model_fields)}"
            )
            overall_pass = False

        else:
            records = list(
                TeacherFreeAfternoon.objects.filter(
                    term=run.term,
                    is_active=True,
                )
            )

            def normalize_day(value):
                text = str(value).upper().strip()

                aliases = {
                    "MONDAY": "MON",
                    "TUESDAY": "TUE",
                    "WEDNESDAY": "WED",
                    "THURSDAY": "THU",
                    "FRIDAY": "FRI",
                }

                return aliases.get(text, text)

            declared = defaultdict(list)

            for record in records:
                teacher_id = getattr(record, "teacher_id", None)
                day = normalize_day(
                    getattr(record, day_field)
                )
                declared[teacher_id].append(day)

            active_teacher_ids = {
                e.teacher_id
                for e in entries
                if is_teaching_entry(e)
                and e.teacher_id is not None
            }

            failures = []

            for teacher_id in sorted(active_teacher_ids):
                days = declared.get(teacher_id, [])

                if len(days) != 1:
                    failures.append(
                        (
                            teacher_id,
                            "must have exactly one free afternoon",
                            days,
                            [],
                        )
                    )
                    continue

                free_day = days[0]

                violations = [
                    e
                    for e in entries
                    if (
                        is_teaching_entry(e)
                        and e.teacher_id == teacher_id
                        and day_code(e) == free_day
                        and e.period.number in AFTERNOON_PERIODS
                    )
                ]

                if violations:
                    failures.append(
                        (
                            teacher_id,
                            "teaching during declared free afternoon",
                            days,
                            violations,
                        )
                    )

            ok = not failures

            self.stdout.write(
                f"FREE-AFTERNOON RECORDS: {len(records)}"
            )
            self.stdout.write(
                f"ACTIVE TEACHERS AUDITED: "
                f"{len(active_teacher_ids)}"
            )
            self.stdout.write(
                f"FREE-AFTERNOON FAILURES: {len(failures)} "
                f"{'PASS' if ok else 'FAIL'}"
            )

            if not ok:
                overall_pass = False

                for teacher_id, reason, days, violations in failures:
                    self.stdout.write(
                        f"  Teacher {teacher_id}: "
                        f"{reason}; declared={days}"
                    )

                    for entry in violations:
                        self.stdout.write(
                            f"    {day_code(entry)}/P{entry.period.number} "
                            f"{subject_code(entry.lesson_requirement.subject)}"
                        )

        # ------------------------------------------------------------
        # FINAL
        # ------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 100)

        if overall_pass:
            self.stdout.write(
                self.style.SUCCESS(
                    "FINAL AUTHORITATIVE GRADE 10 RESULT: PASS"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "FINAL AUTHORITATIVE GRADE 10 RESULT: FAIL"
                )
            )

        self.stdout.write("=" * 100)
        self.stdout.write(
            "READ-ONLY AUDIT — NO DATABASE CHANGES MADE."
        )