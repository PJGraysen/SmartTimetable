from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.academics.models import (
    InstructionalGroup,
    LessonRequirement,
    Subject,
)

from apps.scheduling.models import (
    Period,
    SchedulingRun,
    TeacherAssignment,
    TimetableEntry,
    TimetableVersion,
)


class Command(BaseCommand):
    help = "Read-only forensic audit of Grade 10 contract compliance."

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write(
            "SMARTTIMETABLE PRO — GRADE 10 CONTRACT FORENSIC AUDIT"
        )
        self.stdout.write("=" * 110)
        self.stdout.write("READ-ONLY — NO DATABASE RECORDS ARE MODIFIED.")
        self.stdout.write("")

        # ------------------------------------------------------------
        # AUTHORITATIVE GROUPS
        # ------------------------------------------------------------
        required_codes = ["10E", "10W"]

        self.stdout.write("1. INSTRUCTIONAL GROUP AUTHORITY")
        self.stdout.write("-" * 110)

        groups = InstructionalGroup.objects.filter(
            code__in=required_codes
        ).order_by("code")

        for group in groups:
            self.stdout.write(
                f"  FOUND: id={group.id} "
                f"name={group.name} "
                f"code={group.code} "
                f"is_active={group.is_active}"
            )

        legacy = InstructionalGroup.objects.filter(
            code__in=["10A", "G10A", "Grade10A"]
        )

        # Also catch likely Grade 10A records by name.
        legacy_name = InstructionalGroup.objects.filter(
            name__icontains="Grade 10A"
        )

        legacy_ids = set(legacy.values_list("id", flat=True))
        legacy_ids.update(legacy_name.values_list("id", flat=True))

        if legacy_ids:
            self.stdout.write("")
            self.stdout.write("  LEGACY GRADE 10A RECORDS DETECTED:")
            for group in InstructionalGroup.objects.filter(
                id__in=legacy_ids
            ).order_by("code"):
                self.stdout.write(
                    f"    id={group.id} "
                    f"name={group.name} "
                    f"code={group.code} "
                    f"is_active={group.is_active}"
                )
        else:
            self.stdout.write("  No Grade 10A legacy group detected.")

        self.stdout.write("")

        # ------------------------------------------------------------
        # CURRENT ACTIVE VERSION
        # ------------------------------------------------------------
        self.stdout.write("2. CURRENT TIMETABLE VERSION AUTHORITY")
        self.stdout.write("-" * 110)

        active_versions = TimetableVersion.objects.filter(
            is_active=True
        ).order_by("-version_number")

        self.stdout.write(
            f"  ACTIVE VERSIONS: {active_versions.count()}"
        )

        current = active_versions.first()

        if not current:
            self.stdout.write("  ERROR: No active timetable version.")
            return

        self.stdout.write(
            f"  CURRENT: {current.name} "
            f"version_number={current.version_number}"
        )

        # ------------------------------------------------------------
        # ENTRY ANALYSIS
        # ------------------------------------------------------------
        entries = TimetableEntry.objects.filter(
            timetable_version=current
        )

        self.stdout.write("")
        self.stdout.write("3. CURRENT TIMETABLE ENTRY FORENSICS")
        self.stdout.write("-" * 110)

        self.stdout.write(
            f"  TOTAL ENTRIES: {entries.count()}"
        )

        for code in required_codes:
            group_entries = entries.filter(
                instructional_group__code=code
            )

            self.stdout.write(
                f"  {code}: {group_entries.count()} entries "
                f"(EXPECTED 49)"
            )

        legacy_entries = entries.filter(
            instructional_group__id__in=legacy_ids
        )

        self.stdout.write(
            f"  LEGACY GRADE 10A ENTRIES: {legacy_entries.count()}"
        )

        # ------------------------------------------------------------
        # DAY DISTRIBUTION
        # ------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("4. DAILY TEACHING DISTRIBUTION")
        self.stdout.write("-" * 110)

        expected_daily = {
            "MON": 9,
            "TUE": 10,
            "WED": 10,
            "THU": 10,
            "FRI": 10,
        }

        for code in required_codes:
            self.stdout.write(f"  {code}:")

            group_entries = entries.filter(
                instructional_group__code=code
            )

            for day, expected in expected_daily.items():
                count = group_entries.filter(day=day).count()

                status = "PASS" if count == expected else "FAIL"

                self.stdout.write(
                    f"    {day}: {count} / {expected} [{status}]"
                )

        # ------------------------------------------------------------
        # SUBJECT DISTRIBUTION
        # ------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("5. SUBJECT DISTRIBUTION")
        self.stdout.write("-" * 110)

        required_subjects = {
            "ENG": 5,
            "KIS": 5,
            "EMCM": 5,
            "CRE": 4,
            "PE": 3,
            "CSL": 3,
            "ICT": 2,
            "PRP": 1,
        }

        for code in required_codes:
            self.stdout.write(f"  {code}:")

            group_entries = entries.filter(
                instructional_group__code=code
            )

            for subject_code, expected in required_subjects.items():
                count = group_entries.filter(
                    lesson_requirement__subject__code=subject_code
                ).count()

                status = "PASS" if count == expected else "FAIL"

                self.stdout.write(
                    f"    {subject_code}: {count} / {expected} [{status}]"
                )

        # ------------------------------------------------------------
        # ELECTIVE SUBJECT DISCOVERY
        # ------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("6. ELECTIVE SUBJECTS PRESENT IN CURRENT TIMETABLE")
        self.stdout.write("-" * 110)

        elective_codes = [
            "BIO",
            "MUS",
            "FRE",
            "CHEM",
            "PHY",
            "LIT",
            "GEO",
            "HIST",
            "CS",
            "BUS",
            "AGRI",
        ]

        for code in required_codes:
            self.stdout.write(f"  {code}:")

            group_entries = entries.filter(
                instructional_group__code=code
            )

            for subject_code in elective_codes:
                count = group_entries.filter(
                    lesson_requirement__subject__code=subject_code
                ).count()

                if count:
                    self.stdout.write(
                        f"    {subject_code}: {count}"
                    )

        # ------------------------------------------------------------
        # NON-TEACHING PERIODS
        # ------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("7. PERIOD AUTHORITY")
        self.stdout.write("-" * 110)

        periods = Period.objects.filter(
            is_active=True
        ).order_by("number")

        for period in periods:
            self.stdout.write(
                f"  P{period.number}: "
                f"{period.name} "
                f"{period.start_time}-{period.end_time} "
                f"teaching={period.is_teaching_period} "
                f"part_of_day={period.part_of_day}"
            )

        # ------------------------------------------------------------
        # NULL / ORPHAN CHECKS
        # ------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("8. ENTRY INTEGRITY")
        self.stdout.write("-" * 110)

        null_teacher = entries.filter(teacher__isnull=True).count()
        null_requirement = entries.filter(
            lesson_requirement__isnull=True
        ).count()
        null_period = entries.filter(period__isnull=True).count()
        null_group = entries.filter(
            instructional_group__isnull=True
        ).count()

        self.stdout.write(
            f"  Missing teacher: {null_teacher}"
        )
        self.stdout.write(
            f"  Missing lesson requirement: {null_requirement}"
        )
        self.stdout.write(
            f"  Missing period: {null_period}"
        )
        self.stdout.write(
            f"  Missing instructional group: {null_group}"
        )

        # ------------------------------------------------------------
        # FINAL STRUCTURAL RESULT
        # ------------------------------------------------------------
        expected_total = 98
        actual_total = sum(
            entries.filter(
                instructional_group__code=code
            ).count()
            for code in required_codes
        )

        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("9. CONTRACT STRUCTURAL DECISION")
        self.stdout.write("-" * 110)

        self.stdout.write(
            f"  REQUIRED: 10E = 49 + 10W = 49 = {expected_total}"
        )
        self.stdout.write(
            f"  FOUND:    {actual_total}"
        )

        if actual_total == expected_total:
            self.stdout.write(
                "  RESULT: PASS — entry count matches 49 lessons per group."
            )
        else:
            self.stdout.write(
                f"  RESULT: FAIL — {expected_total - actual_total:+d} "
                "difference from authoritative teaching-entry count."
            )

        self.stdout.write("")
        self.stdout.write(
            "  AUTHORITATIVE ARCHITECTURE:"
        )
        self.stdout.write(
            "    Grade 10E + Grade 10W"
        )
        self.stdout.write(
            "    49 teaching lessons per group"
        )
        self.stdout.write(
            "    Elective blocks are structural groupings, not subjects"
        )
        self.stdout.write(
            "    Grade 10A is legacy and must not be authoritative"
        )
        self.stdout.write(
            "    Breaks/Assembly/Prayers/Activities are non-teaching"
        )
        self.stdout.write("=" * 110)
        self.stdout.write("")
