
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Read-only audit of Grade 10E/10W LessonRequirements and "
        "TimetableEntries through the real persistence relationships."
    )

    def handle(self, *args, **options):
        from apps.academics.models import LessonRequirement
        from apps.scheduling.models import (
            TimetableEntry,
            TimetableVersion,
        )
        from apps.scheduling.models import TeacherAssignment

        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write(
            "SMARTTIMETABLE PRO - GRADE 10 REQUIREMENT / PERSISTENCE AUDIT"
        )
        self.stdout.write("=" * 110)
        self.stdout.write("READ-ONLY: no database records are modified.")
        self.stdout.write("")

        # ==============================================================
        # 1. ACTUAL MODEL RELATIONSHIPS
        # ==============================================================
        self.stdout.write("=" * 110)
        self.stdout.write("1. ACTUAL MODEL RELATIONSHIPS")
        self.stdout.write("=" * 110)

        self.describe_model(TimetableEntry)
        self.describe_model(LessonRequirement)
        self.describe_model(TimetableVersion)
        self.describe_model(TeacherAssignment)

        # ==============================================================
        # 2. FIND GRADE 10E / 10W
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("2. GRADE 10 INSTRUCTIONAL GROUPS")
        self.stdout.write("=" * 110)

        group_field = LessonRequirement._meta.get_field(
            "instructional_group"
        )

        group_model = group_field.remote_field.model

        groups = list(
            group_model.objects.filter(
                name__in=[
                    "Grade 10E",
                    "Grade 10W",
                    "Grade 10A",
                ]
            ).order_by("name")
        )

        for group in groups:
            self.stdout.write(
                f"GROUP: id={group.pk} "
                f"name={getattr(group, 'name', group)}"
            )

        grade10_groups = [
            group
            for group in groups
            if getattr(group, "name", "").strip().lower()
            in {"grade 10e", "grade 10w"}
        ]

        if not grade10_groups:
            self.stdout.write(
                self.style.ERROR(
                    "NO Grade 10E / Grade 10W instructional groups found."
                )
            )
            return

        # ==============================================================
        # 3. DETERMINE ACTIVE TERMS
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("3. ACTIVE GRADE 10 REQUIREMENTS")
        self.stdout.write("=" * 110)

        requirements = list(
            LessonRequirement.objects
            .filter(
                instructional_group__in=grade10_groups,
                is_active=True,
            )
            .select_related(
                "term",
                "instructional_group",
                "subject",
            )
            .order_by(
                "instructional_group__name",
                "subject__code",
                "subject__name",
                "id",
            )
        )

        if not requirements:
            self.stdout.write(
                self.style.ERROR(
                    "NO active Grade 10E/Grade 10W LessonRequirements found."
                )
            )
            return

        grouped = defaultdict(list)

        for requirement in requirements:
            grouped[
                requirement.instructional_group.name
            ].append(requirement)

        for group_name in sorted(grouped):
            reqs = grouped[group_name]

            self.stdout.write("")
            self.stdout.write(f"--- {group_name} ---")

            total = 0

            for req in reqs:
                weekly = int(req.lessons_per_week or 0)
                total += weekly

                subject = req.subject

                self.stdout.write(
                    f"REQ {str(req.pk):<38} "
                    f"SUBJECT={getattr(subject, 'code', '') or '-':<12} "
                    f"{getattr(subject, 'name', 'UNKNOWN'):<35} "
                    f"WEEKLY={weekly:<3} "
                    f"TERM={getattr(req.term, 'name', str(req.term))}"
                )

            self.stdout.write(
                f"TOTAL REQUIRED WEEKLY PERIODS: {total}"
            )

        # ==============================================================
        # 4. TEACHER ASSIGNMENTS
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("4. TEACHER ASSIGNMENTS")
        self.stdout.write("=" * 110)

        assignments = list(
            TeacherAssignment.objects
            .filter(
                lesson_requirement__in=requirements,
            )
            .select_related(
                "lesson_requirement",
                "teacher",
            )
            .order_by(
                "lesson_requirement__instructional_group__name",
                "lesson_requirement__subject__code",
                "lesson_requirement__subject__name",
                "id",
            )
        )

        assignments_by_requirement = defaultdict(list)

        for assignment in assignments:
            assignments_by_requirement[
                assignment.lesson_requirement_id
            ].append(assignment)

        for group_name in sorted(grouped):
            self.stdout.write("")
            self.stdout.write(f"--- {group_name} ---")

            for req in grouped[group_name]:
                subject = req.subject
                req_assignments = assignments_by_requirement.get(
                    req.pk,
                    [],
                )

                if not req_assignments:
                    self.stdout.write(
                        f"REQ {str(req.pk):<38} "
                        f"{getattr(subject, 'code', '') or '-':<12} "
                        f"{getattr(subject, 'name', 'UNKNOWN'):<35} "
                        f"TEACHER ASSIGNMENTS: NONE"
                    )
                    continue

                for assignment in req_assignments:
                    teacher = assignment.teacher

                    self.stdout.write(
                        f"REQ {str(req.pk):<38} "
                        f"{getattr(subject, 'code', '') or '-':<12} "
                        f"{getattr(subject, 'name', 'UNKNOWN'):<35} "
                        f"TEACHER={self.teacher_name(teacher)}"
                    )

        # ==============================================================
        # 5. LOCATE VERSION 82
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("5. TIMETABLE VERSION v82")
        self.stdout.write("=" * 110)

        version = (
            TimetableVersion.objects
            .filter(version_number=82)
            .order_by("-pk")
            .first()
        )

        if version is None:
            self.stdout.write(
                self.style.ERROR(
                    "TIMETABLE VERSION 82 WAS NOT FOUND."
                )
            )
            return

        self.stdout.write(f"VERSION ID: {version.pk}")
        self.stdout.write(f"VERSION NAME: {version.name}")
        self.stdout.write(
            f"VERSION NUMBER: {version.version_number}"
        )
        self.stdout.write(
            f"TERM: {getattr(version.term, 'name', version.term)}"
        )
        self.stdout.write(
            f"ACTIVE: {version.is_active}"
        )
        self.stdout.write(
            f"PUBLISHED: {version.is_published}"
        )

        # ==============================================================
        # 6. PERSISTED GRADE 10 ENTRIES
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("6. PERSISTED GRADE 10E / GRADE 10W ENTRIES IN v82")
        self.stdout.write("=" * 110)

        entries = list(
            TimetableEntry.objects
            .filter(
                timetable_version=version,
                instructional_group__in=grade10_groups,
            )
            .select_related(
                "lesson_requirement",
                "lesson_requirement__subject",
                "lesson_requirement__instructional_group",
                "lesson_requirement__term",
                "instructional_group",
                "teacher",
                "period",
                "room",
            )
            .order_by(
                "instructional_group__name",
                "day",
                "period",
                "id",
            )
        )

        self.stdout.write(
            f"TOTAL GRADE 10E/10W ENTRIES IN v82: {len(entries)}"
        )

        persisted_by_requirement = Counter()

        for entry in entries:
            req = entry.lesson_requirement
            subject = req.subject if req else None
            group = entry.instructional_group
            period = entry.period

            persisted_by_requirement[
                req.pk if req else None
            ] += 1

            self.stdout.write(
                f"{str(entry.day):<6} "
                f"{self.period_label(period):<12} "
                f"{getattr(group, 'name', '-'):<15} "
                f"{getattr(subject, 'code', '') or '-':<12} "
                f"{getattr(subject, 'name', 'UNKNOWN'):<35} "
                f"REQ={str(req.pk) if req else '-':<38} "
                f"TEACHER={self.teacher_name(entry.teacher):<28} "
                f"ROOM={self.room_name(entry.room)}"
            )

        # ==============================================================
        # 7. REQUIREMENT VS PERSISTED COUNTS
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("7. REQUIREMENT VS PERSISTED OCCURRENCE COUNTS")
        self.stdout.write("=" * 110)

        missing = []
        excess = []
        exact = []

        for group_name in sorted(grouped):
            self.stdout.write("")
            self.stdout.write(f"--- {group_name} ---")

            for req in grouped[group_name]:
                subject = req.subject

                required = int(req.lessons_per_week or 0)
                persisted = persisted_by_requirement.get(
                    req.pk,
                    0,
                )

                if persisted == required:
                    status = "OK"
                    exact.append(req)
                elif persisted < required:
                    status = "MISSING"
                    missing.append(req)
                else:
                    status = "EXCESS"
                    excess.append(req)

                self.stdout.write(
                    f"REQ {str(req.pk):<38} "
                    f"{getattr(subject, 'code', '') or '-':<12} "
                    f"{getattr(subject, 'name', 'UNKNOWN'):<35} "
                    f"REQUIRED={required:<3} "
                    f"PERSISTED={persisted:<3} "
                    f"{status}"
                )

        # ==============================================================
        # 8. SUBJECT AGGREGATES
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("8. PERSISTED SUBJECT AGGREGATES")
        self.stdout.write("=" * 110)

        aggregate = Counter()

        for entry in entries:
            req = entry.lesson_requirement
            subject = req.subject if req else None
            group = entry.instructional_group

            key = (
                getattr(group, "name", "-"),
                getattr(subject, "code", "")
                or getattr(subject, "name", "UNKNOWN"),
            )

            aggregate[key] += 1

        for (group_name, subject_code), count in sorted(
            aggregate.items()
        ):
            self.stdout.write(
                f"{group_name:<15} "
                f"{subject_code:<15} "
                f"PERSISTED={count}"
            )

        # ==============================================================
        # 9. LEGACY / WRONG GROUP CHECK
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("9. VERSION v82 NON-GRADE-10 CONTAMINATION CHECK")
        self.stdout.write("=" * 110)

        all_v82_entries = list(
            TimetableEntry.objects
            .filter(
                timetable_version=version,
            )
            .select_related(
                "instructional_group",
                "lesson_requirement",
                "lesson_requirement__subject",
                "teacher",
                "period",
                "room",
            )
            .order_by(
                "instructional_group__name",
                "day",
                "period",
                "id",
            )
        )

        non_grade10 = [
            entry
            for entry in all_v82_entries
            if entry.instructional_group_id
            not in {group.pk for group in grade10_groups}
        ]

        self.stdout.write(
            f"TOTAL v82 ENTRIES: {len(all_v82_entries)}"
        )
        self.stdout.write(
            f"GRADE 10E/10W ENTRIES: {len(entries)}"
        )
        self.stdout.write(
            f"NON-GRADE-10 ENTRIES: {len(non_grade10)}"
        )

        if non_grade10:
            self.stdout.write("")
            self.stdout.write("NON-GRADE-10 ENTRIES:")

            for entry in non_grade10:
                req = entry.lesson_requirement
                subject = req.subject if req else None

                self.stdout.write(
                    f"{str(entry.day):<6} "
                    f"{self.period_label(entry.period):<12} "
                    f"{getattr(entry.instructional_group, 'name', '-'):<20} "
                    f"{getattr(subject, 'code', '') or '-':<12} "
                    f"{getattr(subject, 'name', 'UNKNOWN'):<35} "
                    f"REQ={str(req.pk) if req else '-'}"
                )

        # ==============================================================
        # 10. GRADE 10A LEGACY REQUIREMENT CHECK
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("10. LEGACY GRADE 10A REQUIREMENT CHECK")
        self.stdout.write("=" * 110)

        grade10a = next(
            (
                group
                for group in groups
                if getattr(group, "name", "").strip().lower()
                == "grade 10a"
            ),
            None,
        )

        if grade10a:
            legacy = list(
                LessonRequirement.objects
                .filter(
                    instructional_group=grade10a,
                    is_active=True,
                )
                .select_related("subject", "term")
                .order_by(
                    "subject__code",
                    "subject__name",
                    "id",
                )
            )

            self.stdout.write(
                f"ACTIVE GRADE 10A REQUIREMENTS: {len(legacy)}"
            )

            for req in legacy:
                self.stdout.write(
                    f"REQ {str(req.pk):<38} "
                    f"{getattr(req.subject, 'code', '') or '-':<12} "
                    f"{getattr(req.subject, 'name', 'UNKNOWN'):<35} "
                    f"WEEKLY={int(req.lessons_per_week or 0)}"
                )
        else:
            self.stdout.write(
                "NO Grade 10A instructional group exists."
            )

        # ==============================================================
        # 11. LOCKED BUSINESS STRUCTURE
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("11. LOCKED GRADE 10 ACADEMIC STRUCTURE")
        self.stdout.write("=" * 110)

        self.stdout.write("CORE / STANDALONE:")
        self.stdout.write("  ICT")
        self.stdout.write("  PRP")

        self.stdout.write("")
        self.stdout.write("OPTION 1:")
        self.stdout.write("  BIOLOGY")
        self.stdout.write("  MUSIC")
        self.stdout.write("  FRENCH")

        self.stdout.write("")
        self.stdout.write("OPTION 2:")
        self.stdout.write("  CHEMISTRY")
        self.stdout.write("  PHYSICS")
        self.stdout.write("  LITERATURE")

        self.stdout.write("")
        self.stdout.write("OPTION 3:")
        self.stdout.write("  GEOGRAPHY")
        self.stdout.write("  HISTORY")
        self.stdout.write("  GOVERNMENT")
        self.stdout.write("  COMPUTER SCIENCE")

        self.stdout.write("")
        self.stdout.write("OPTION 4:")
        self.stdout.write("  BUSINESS")
        self.stdout.write("  AGRICULTURE")

        self.stdout.write("")
        self.stdout.write(
            "MUSIC = OPTION 1 ELECTIVE. "
            "MUSIC MUST NOT BE TREATED AS STANDALONE."
        )

        # ==============================================================
        # 12. SUMMARY
        # ==============================================================
        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("12. AUDIT SUMMARY")
        self.stdout.write("=" * 110)

        required_total = sum(
            int(req.lessons_per_week or 0)
            for req in requirements
        )

        persisted_total = len(entries)

        self.stdout.write(
            f"ACTIVE GRADE 10E/10W REQUIREMENTS: {len(requirements)}"
        )
        self.stdout.write(
            f"REQUIRED WEEKLY PERIODS ACROSS E/W: {required_total}"
        )
        self.stdout.write(
            f"PERSISTED v82 GRADE 10E/10W ENTRIES: {persisted_total}"
        )
        self.stdout.write(
            f"EXACT REQUIREMENT COUNTS: {len(exact)}"
        )
        self.stdout.write(
            f"MISSING REQUIREMENTS: {len(missing)}"
        )
        self.stdout.write(
            f"EXCESS REQUIREMENTS: {len(excess)}"
        )

        self.stdout.write("")
        self.stdout.write(
            "PERSISTENCE CHAIN AUDITED:"
        )
        self.stdout.write(
            "TimetableEntry -> LessonRequirement -> Subject"
        )
        self.stdout.write(
            "TimetableEntry -> InstructionalGroup"
        )
        self.stdout.write(
            "LessonRequirement -> TeacherAssignment -> Teacher"
        )
        self.stdout.write(
            "TimetableEntry -> Period / Room / Day"
        )

        self.stdout.write("")
        self.stdout.write(
            "NO SOLVER, TIMETABLE ENTRY, OR REQUIREMENT RECORD WAS MODIFIED."
        )

        self.stdout.write("")
        self.stdout.write("=" * 110)
        self.stdout.write("END AUDIT")
        self.stdout.write("=" * 110)
        self.stdout.write("")

    # ==================================================================
    # HELPERS
    # ==================================================================

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

    @staticmethod
    def teacher_name(teacher):
        if teacher is None:
            return "-"

        for field in [
            "name",
            "full_name",
            "employee_name",
            "display_name",
        ]:
            value = getattr(teacher, field, None)

            if value:
                return str(value)

        first = getattr(teacher, "first_name", "")
        last = getattr(teacher, "last_name", "")

        combined = f"{first} {last}".strip()

        return combined or str(teacher)

    @staticmethod
    def room_name(room):
        if room is None:
            return "-"

        for field in [
            "name",
            "code",
            "room_number",
        ]:
            value = getattr(room, field, None)

            if value:
                return str(value)

        return str(room)

    @staticmethod
    def period_label(period):
        if period is None:
            return "-"

        values = []

        for field in [
            "period_number",
            "number",
            "sequence",
            "order",
            "name",
            "code",
            "label",
            "start_time",
            "end_time",
        ]:
            value = getattr(period, field, None)

            if value is not None:
                values.append(f"{field}={value}")

        if values:
            return "|".join(values)

        return str(period)
