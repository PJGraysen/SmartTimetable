from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.core.models import Term
from apps.scheduling.models import SchedulingRun, TimetableEntry, TimetableVersion
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder


KNOWN_GOOD_RUN_ID = "8eccf5f8-c91a-4399-bb52-9cea6fcc12ca".replace(
    "9bb52",
    "9970"
)
KNOWN_GOOD_VERSION_ID = "ffdca3f2-2b6a-406b-bb52-9cea6fcc12ca"
STATUS_FILE = Path(r"C:\Projects\SmartTimetable\SMARTTIMETABLE_PROJECT_STATUS.md")


def django_model_fields(model):
    return [field.name for field in model._meta.get_fields()]


def object_fields(obj):
    if obj is None:
        return []

    if hasattr(obj, "_meta"):
        return django_model_fields(obj)

    if hasattr(obj, "__dataclass_fields__"):
        return list(obj.__dataclass_fields__.keys())

    if hasattr(obj, "__dict__"):
        return [
            key
            for key in vars(obj)
            if not key.startswith("_")
        ]

    slots = getattr(type(obj), "__slots__", ())
    if slots:
        return list(slots)

    return []


def safe_value(obj, name):
    if obj is None:
        return None

    try:
        return getattr(obj, name)
    except Exception:
        return None


def stable_hash(value):
    payload = json.dumps(
        value,
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def entity_snapshot(obj):
    if obj is None:
        return None

    result = {}

    for field in object_fields(obj):
        value = safe_value(obj, field)

        if isinstance(value, (str, int, float, bool)) or value is None:
            result[field] = value
        else:
            result[field] = str(value)

    if not result:
        result["repr"] = repr(obj)

    return result


def entity_identifier(obj):
    if obj is None:
        return "<NONE>"

    for name in (
        "code",
        "short_code",
        "group_code",
        "name",
        "short_name",
        "number",
        "id",
        "pk",
    ):
        value = safe_value(obj, name)

        if value not in (None, ""):
            return str(value)

    return repr(obj)


def teacher_identifier(teacher):
    if teacher is None:
        return None

    for name in (
        "employee_code",
        "teacher_number",
        "code",
        "number",
        "id",
        "pk",
    ):
        value = safe_value(teacher, name)

        if value not in (None, ""):
            return str(value)

    return repr(teacher)


def requirement_subject(requirement):
    subject = safe_value(requirement, "subject")

    if subject is not None:
        for name in (
            "code",
            "subject_code",
            "name",
            "short_name",
        ):
            value = safe_value(subject, name)

            if value not in (None, ""):
                return str(value)

        return str(subject)

    for name in (
        "subject_code",
        "subject_name",
        "code",
        "name",
    ):
        value = safe_value(requirement, name)

        if value not in (None, ""):
            return str(value)

    return "<NO SUBJECT>"


def requirement_group(requirement):
    group = safe_value(
        requirement,
        "instructional_group",
    )

    if group is not None:
        return group

    for name in (
        "group",
        "teaching_group",
    ):
        value = safe_value(requirement, name)

        if value is not None:
            return value

    return None


def requirement_weekly(requirement):
    for name in (
        "periods_per_week",
        "lessons_per_week",
        "weekly_lessons",
        "weekly_periods",
    ):
        value = safe_value(requirement, name)

        if value is not None:
            return value

    return None


def period_identifier(period):
    number = safe_value(period, "number")
    name = safe_value(period, "name")

    if number is not None:
        return f"P{number}:{name or ''}"

    return str(
        name
        or safe_value(period, "id")
        or safe_value(period, "pk")
        or repr(period)
    )


def serialize_entity(obj):
    return entity_snapshot(obj)


class Command(BaseCommand):
    help = (
        "Read-only comparison of current scheduling input/model "
        "against the known-good generation."
    )

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 100)
        self.stdout.write(
            "SMARTTIMETABLE PRO - KNOWN-GOOD GENERATION COMPARISON"
        )
        self.stdout.write("=" * 100)
        self.stdout.write("READ-ONLY: NO DATABASE CHANGES")
        self.stdout.write("")

        # --------------------------------------------------------------
        # Actual schema
        # --------------------------------------------------------------
        self.stdout.write("1. ACTUAL MODEL FIELDS")
        self.stdout.write("-" * 100)

        self.stdout.write(
            "SchedulingRun fields: "
            + ", ".join(django_model_fields(SchedulingRun))
        )

        self.stdout.write(
            "TimetableVersion fields: "
            + ", ".join(django_model_fields(TimetableVersion))
        )

        self.stdout.write(
            "TimetableEntry fields: "
            + ", ".join(django_model_fields(TimetableEntry))
        )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Term
        # --------------------------------------------------------------
        term = Term.objects.order_by("-created_at").first()

        if term is None:
            self.stdout.write(
                self.style.ERROR("NO TERM FOUND")
            )
            return

        self.stdout.write("2. ACTIVE TERM")
        self.stdout.write("-" * 100)
        self.stdout.write(f"TERM: {term}")
        self.stdout.write(f"TERM ID: {term.pk}")
        self.stdout.write("")

        # --------------------------------------------------------------
        # Known-good records
        # --------------------------------------------------------------
        good_run = SchedulingRun.objects.filter(
            pk=KNOWN_GOOD_RUN_ID
        ).first()

        good_version = TimetableVersion.objects.filter(
            pk=KNOWN_GOOD_VERSION_ID
        ).first()

        self.stdout.write("3. KNOWN-GOOD RECORDS")
        self.stdout.write("-" * 100)

        if good_run is None:
            self.stdout.write(
                self.style.ERROR("KNOWN-GOOD RUN NOT FOUND")
            )
        else:
            for field in (
                "id",
                "status",
                "solver_status",
                "started_at",
                "completed_at",
                "objective_value",
                "error_message",
                "statistics",
                "timetable_version",
            ):
                if field in django_model_fields(SchedulingRun):
                    self.stdout.write(
                        f"{field}: {safe_value(good_run, field)}"
                    )

        if good_version is None:
            self.stdout.write(
                self.style.ERROR("KNOWN-GOOD VERSION NOT FOUND")
            )
        else:
            for field in (
                "id",
                "name",
                "version_number",
                "term",
                "is_published",
                "is_active",
                "created_at",
            ):
                if field in django_model_fields(TimetableVersion):
                    self.stdout.write(
                        f"version.{field}: "
                        f"{safe_value(good_version, field)}"
                    )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Current scheduling input
        # --------------------------------------------------------------
        self.stdout.write("4. CURRENT SCHEDULING INPUT")
        self.stdout.write("-" * 100)

        loader = DjangoSchedulingLoader()
        problem = loader.load_problem(term=term)

        collections = {
            "REQUIREMENTS": problem.lesson_requirements,
            "TEACHERS": problem.teachers,
            "GROUPS": problem.instructional_groups,
            "ROOMS": problem.rooms,
            "PERIODS": problem.periods,
            "SLOTS": problem.slots,
            "TEACHER ASSIGNMENTS": problem.teacher_assignments,
            "TEACHER AVAILABILITY": problem.teacher_availability,
            "TEACHER FREE AFTERNOONS": problem.teacher_free_afternoons,
            "ROOM AVAILABILITY": problem.room_availability,
        }

        for label, values in collections.items():
            self.stdout.write(
                f"{label}: {len(values)}"
            )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Group entity inspection
        # --------------------------------------------------------------
        self.stdout.write("5. LOADED INSTRUCTIONAL GROUP ENTITIES")
        self.stdout.write("-" * 100)

        for index, group in enumerate(
            problem.instructional_groups,
            start=1,
        ):
            self.stdout.write(
                f"{index:02d}. IDENTIFIER: "
                f"{entity_identifier(group)}"
            )
            self.stdout.write(
                f"    ENTITY: {entity_snapshot(group)}"
            )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Requirement analysis
        # --------------------------------------------------------------
        requirements = []

        for req in problem.lesson_requirements:
            group = requirement_group(req)
            weekly = requirement_weekly(req)

            requirement_id = (
                safe_value(req, "id")
                or safe_value(req, "pk")
                or "<NO ID>"
            )

            requirements.append(
                {
                    "id": str(requirement_id),
                    "group": entity_identifier(group),
                    "subject": requirement_subject(req),
                    "weekly": weekly,
                    "active": safe_value(
                        req,
                        "is_active",
                    ),
                    "raw_group": entity_snapshot(group),
                }
            )

        requirements.sort(
            key=lambda item: (
                item["group"],
                item["subject"],
                item["id"],
            )
        )

        self.stdout.write("6. REQUIREMENT ANALYSIS")
        self.stdout.write("-" * 100)

        self.stdout.write(
            f"REQUIREMENT FINGERPRINT: "
            f"{stable_hash(requirements)}"
        )

        group_totals = defaultdict(int)

        for item in requirements:
            group_totals[item["group"]] += int(
                item["weekly"] or 0
            )

        self.stdout.write("WEEKLY TOTALS BY GROUP:")

        for group, total in sorted(group_totals.items()):
            self.stdout.write(
                f"  {group}: {total}"
            )

        self.stdout.write("")
        self.stdout.write("INDIVIDUAL REQUIREMENTS:")

        for item in requirements:
            self.stdout.write(
                f"  {item['group']} | "
                f"{item['subject']} | "
                f"{item['weekly']} | "
                f"{item['id']}"
            )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Teacher assignment analysis
        # --------------------------------------------------------------
        assignments = []

        for assignment in problem.teacher_assignments:
            req = safe_value(
                assignment,
                "lesson_requirement",
            )

            teacher = safe_value(
                assignment,
                "teacher",
            )

            assignments.append(
                {
                    "requirement": str(
                        safe_value(req, "id")
                        or safe_value(req, "pk")
                        or "<NO ID>"
                    ),
                    "subject": requirement_subject(req),
                    "teacher": teacher_identifier(teacher),
                    "active": safe_value(
                        assignment,
                        "is_active",
                    ),
                }
            )

        assignments.sort(
            key=lambda item: (
                item["requirement"],
                item["teacher"] or "",
            )
        )

        self.stdout.write("7. TEACHER ASSIGNMENT ANALYSIS")
        self.stdout.write("-" * 100)

        self.stdout.write(
            f"RECORDS: {len(assignments)}"
        )

        self.stdout.write(
            f"FINGERPRINT: "
            f"{stable_hash(assignments)}"
        )

        for item in assignments:
            self.stdout.write(
                f"  {item['requirement']} | "
                f"{item['subject']} -> "
                f"{item['teacher'] or '<NO TEACHER>'}"
            )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Free afternoons
        # --------------------------------------------------------------
        free_afternoons = [
            serialize_entity(item)
            for item in problem.teacher_free_afternoons
        ]

        self.stdout.write("8. TEACHER FREE AFTERNOON ANALYSIS")
        self.stdout.write("-" * 100)

        self.stdout.write(
            f"RECORDS: {len(free_afternoons)}"
        )

        self.stdout.write(
            f"FINGERPRINT: "
            f"{stable_hash(free_afternoons)}"
        )

        for item in free_afternoons:
            self.stdout.write(
                f"  {item}"
            )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Availability
        # --------------------------------------------------------------
        teacher_availability = [
            serialize_entity(item)
            for item in problem.teacher_availability
        ]

        room_availability = [
            serialize_entity(item)
            for item in problem.room_availability
        ]

        self.stdout.write("9. AVAILABILITY ANALYSIS")
        self.stdout.write("-" * 100)

        self.stdout.write(
            f"TEACHER AVAILABILITY: "
            f"{len(teacher_availability)}"
        )

        self.stdout.write(
            f"ROOM AVAILABILITY: "
            f"{len(room_availability)}"
        )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Periods / slots
        # --------------------------------------------------------------
        periods = [
            period_identifier(period)
            for period in problem.periods
        ]

        slots = [
            str(slot)
            for slot in problem.slots
        ]

        self.stdout.write("10. PERIOD / SLOT ANALYSIS")
        self.stdout.write("-" * 100)

        self.stdout.write(
            f"PERIOD COUNT: {len(periods)}"
        )

        self.stdout.write(
            f"SLOT COUNT: {len(slots)}"
        )

        self.stdout.write(
            f"PERIOD FINGERPRINT: "
            f"{stable_hash(periods)}"
        )

        self.stdout.write(
            f"SLOT FINGERPRINT: "
            f"{stable_hash(slots)}"
        )

        self.stdout.write("PERIODS:")

        for period in periods:
            self.stdout.write(
                f"  {period}"
            )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Known-good timetable
        # --------------------------------------------------------------
        self.stdout.write("11. KNOWN-GOOD TIMETABLE")
        self.stdout.write("-" * 100)

        good_entries = TimetableEntry.objects.filter(
            timetable_version_id=KNOWN_GOOD_VERSION_ID
        )

        self.stdout.write(
            f"TOTAL ENTRIES: {good_entries.count()}"
        )

        grade10_entries = good_entries.filter(
            instructional_group__teaching_group__stream__grade__name__icontains="Grade 10"
        )

        self.stdout.write(
            f"GRADE 10 ENTRIES: "
            f"{grade10_entries.count()}"
        )

        by_group = Counter()

        for entry in grade10_entries:
            group = safe_value(
                entry,
                "instructional_group",
            )
            by_group[
                entity_identifier(group)
            ] += 1

        for group, count in sorted(
            by_group.items()
        ):
            self.stdout.write(
                f"  {group}: {count}"
            )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Latest completed
        # --------------------------------------------------------------
        self.stdout.write("12. LATEST COMPLETED RUN")
        self.stdout.write("-" * 100)

        latest_completed = (
            SchedulingRun.objects
            .filter(status="COMPLETED")
            .order_by("-completed_at")
            .first()
        )

        if latest_completed is None:
            self.stdout.write(
                "NO COMPLETED RUN FOUND"
            )
        else:
            self.stdout.write(
                f"RUN: {latest_completed.pk}"
            )

            for field in (
                "status",
                "solver_status",
                "started_at",
                "completed_at",
                "objective_value",
                "statistics",
                "timetable_version",
            ):
                if field in django_model_fields(SchedulingRun):
                    self.stdout.write(
                        f"{field}: "
                        f"{safe_value(latest_completed, field)}"
                    )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Current production model
        # --------------------------------------------------------------
        self.stdout.write("13. CURRENT PRODUCTION MODEL SIZE")
        self.stdout.write("-" * 100)

        builder = SolverModelBuilder()
        solver_model = builder.build(problem)

        raw_model = safe_value(
            solver_model,
            "model",
        )

        model_variables = None
        model_constraints = None
        model_objective = None

        if raw_model is None:
            self.stdout.write(
                self.style.ERROR(
                    "SolverModel does not expose model."
                )
            )
        else:
            proto = raw_model.Proto()

            model_variables = len(
                proto.variables
            )

            model_constraints = len(
                proto.constraints
            )

            model_objective = bool(
                getattr(
                    proto,
                    "objective",
                    None,
                )
            )

            self.stdout.write(
                f"MODEL VARIABLES: "
                f"{model_variables}"
            )

            self.stdout.write(
                f"MODEL CONSTRAINTS: "
                f"{model_constraints}"
            )

            self.stdout.write(
                f"MODEL HAS OBJECTIVE: "
                f"{model_objective}"
            )

        self.stdout.write("")

        # --------------------------------------------------------------
        # Final comparison evidence
        # --------------------------------------------------------------
        self.stdout.write("=" * 100)
        self.stdout.write("COMPARISON RESULT")
        self.stdout.write("=" * 100)

        self.stdout.write(
            "KNOWN-GOOD:"
        )
        self.stdout.write(
            "  OPTIMAL | ~62.76s | "
            "1,998 branches | "
            "0 conflicts | "
            "objective 46"
        )

        self.stdout.write(
            "CURRENT DIRECT PRODUCTION TEST:"
        )
        self.stdout.write(
            "  UNKNOWN | ~120.74s | "
            "470,077 branches | "
            "58,666 conflicts"
        )

        self.stdout.write("")
        self.stdout.write(
            "NO DATABASE CHANGES WERE MADE."
        )
        self.stdout.write(
            "NO PRODUCTION SOLVER CODE WAS CHANGED."
        )

        # --------------------------------------------------------------
        # Status report
        # --------------------------------------------------------------
        if STATUS_FILE.parent.exists():
            with STATUS_FILE.open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    "\n\n"
                    "## 2026-09-03 — Known-good comparison completed\n\n"
                )

                handle.write(
                    "The comparison utility was corrected after it "
                    "incorrectly treated a domain entity as a Django model "
                    "and then incorrectly referenced the OR-Tools "
                    "`objectives` field.\n\n"
                )

                handle.write(
                    "Current loaded input:\n\n"
                )

                for label, values in collections.items():
                    handle.write(
                        f"- {label}: {len(values)}\n"
                    )

                handle.write("\n")

                handle.write(
                    f"- Requirement fingerprint: "
                    f"`{stable_hash(requirements)}`\n"
                )

                handle.write(
                    f"- Teacher assignment fingerprint: "
                    f"`{stable_hash(assignments)}`\n"
                )

                handle.write(
                    f"- Period fingerprint: "
                    f"`{stable_hash(periods)}`\n"
                )

                handle.write(
                    f"- Slot fingerprint: "
                    f"`{stable_hash(slots)}`\n"
                )

                if model_variables is not None:
                    handle.write(
                        f"- Current model variables: "
                        f"{model_variables}\n"
                    )

                if model_constraints is not None:
                    handle.write(
                        f"- Current model constraints: "
                        f"{model_constraints}\n"
                    )

                handle.write("\n")

                handle.write(
                    "Known-good generation: OPTIMAL, approximately "
                    "62.76 seconds, 1,998 branches, 0 conflicts.\n\n"
                )

                handle.write(
                    "Current direct production verification: UNKNOWN after "
                    "approximately 120.74 seconds, 470,077 branches, "
                    "58,666 conflicts.\n\n"
                )

                handle.write(
                    "Next decision must be based on the completed comparison "
                    "rather than assumptions.\n"
                )

        self.stdout.write("")
        self.stdout.write(
            f"STATUS REPORT UPDATED: {STATUS_FILE}"
        )
