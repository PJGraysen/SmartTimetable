from __future__ import annotations

from collections import Counter, defaultdict

from django.core.management.base import BaseCommand

from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver
from apps.scheduling.models import SchedulingRun


class Command(BaseCommand):
    help = "Read-only forensic audit of the current production scheduling model."

    def handle(self, *args, **options):
        self.stdout.write("=" * 78)
        self.stdout.write("SMARTTIMETABLE CONSTRAINT CONFLICT CORE AUDIT")
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: YES")
        self.stdout.write("DATABASE MUTATION: NO")
        self.stdout.write("PRODUCTION MODEL MUTATION: NO")
        self.stdout.write("")

        run = (
            SchedulingRun.objects
            .select_related("term", "timetable_version")
            .filter(status="COMPLETED")
            .order_by("-completed_at")
            .first()
        )

        if run is None:
            raise RuntimeError("No completed SchedulingRun exists.")

        term = run.term

        self.stdout.write("AUTHORITATIVE TERM")
        self.stdout.write(f"  TERM ID:    {term.id}")
        self.stdout.write(f"  TERM NAME:  {term.name}")
        self.stdout.write(f"  RUN ID:     {run.id}")
        self.stdout.write(f"  RUN STATUS: {run.status}")
        self.stdout.write("")

        problem = DjangoSchedulingLoader().load_problem(term=term)
        solver_model = SolverModelBuilder().build(problem)

        self.stdout.write("PROBLEM")
        self.stdout.write(f"  REQUIREMENTS:           {len(problem.lesson_requirements)}")
        self.stdout.write(f"  TEACHERS:               {len(problem.teachers)}")
        self.stdout.write(f"  GROUPS:                 {len(problem.instructional_groups)}")
        self.stdout.write(f"  ROOMS:                  {len(problem.rooms)}")
        self.stdout.write(f"  PERIODS:                {len(problem.periods)}")
        self.stdout.write(f"  SLOTS:                  {len(problem.slots)}")
        self.stdout.write(
            f"  TEACHER ASSIGNMENTS:    {len(problem.teacher_assignments)}"
        )
        self.stdout.write(
            f"  TEACHER AVAILABILITY:   {len(problem.teacher_availability)}"
        )
        self.stdout.write(
            f"  TEACHER FREE AFTERNOONS:{len(problem.teacher_free_afternoons)}"
        )
        self.stdout.write(
            f"  ROOM AVAILABILITY:      {len(problem.room_availability)}"
        )
        self.stdout.write("")

        self.stdout.write("GRADE 10 GROUPS")
        grade10_ids = set()

        for group in problem.instructional_groups:
            code = str(getattr(group, "code", "") or "")
            name = str(getattr(group, "name", "") or "")

            if code.upper() in {"10E", "10W"} or name.upper() in {
                "GRADE 10E",
                "GRADE 10W",
            }:
                grade10_ids.add(group.id)
                self.stdout.write(
                    f"  ID={group.id} CODE={code} NAME={name}"
                )

        self.stdout.write("")
        self.stdout.write("-" * 78)
        self.stdout.write("EXACT PRODUCTION MODEL")
        self.stdout.write("-" * 78)

        proto = solver_model.model.Proto()

        self.stdout.write(f"  VARIABLES:   {len(proto.variables)}")
        self.stdout.write(f"  CONSTRAINTS: {len(proto.constraints)}")
        self.stdout.write("")

        # ------------------------------------------------------------------
        # AssignmentVariable -> CP-SAT variable index
        # ------------------------------------------------------------------
        assignment_by_cp_index = {}

        for key, assignment in solver_model.variables.items():
            cp_var = assignment.variable

            try:
                cp_index = cp_var.Index()
            except AttributeError:
                cp_index = getattr(cp_var, "index", None)

            if cp_index is not None:
                assignment_by_cp_index[int(cp_index)] = assignment

        self.stdout.write("ASSIGNMENT VARIABLE INDEX MAP")
        self.stdout.write(
            f"  ASSIGNMENT VARIABLES MAPPED: {len(assignment_by_cp_index)}"
        )
        self.stdout.write("")

        # ------------------------------------------------------------------
        # Actual runtime slot structure.
        #
        # The previous audit inspected slot.day_of_week, which is not the
        # runtime field used by AssignmentVariable.  Show all non-callable
        # public attributes of one slot so this audit records the real model.
        # ------------------------------------------------------------------
        self.stdout.write("RUNTIME SLOT STRUCTURE")

        if problem.slots:
            sample_slot = problem.slots[0]
            self.stdout.write(f"  TYPE: {type(sample_slot)}")

            attrs = {}
            for name in dir(sample_slot):
                if name.startswith("_"):
                    continue

                try:
                    value = getattr(sample_slot, name)
                except Exception:
                    continue

                if callable(value):
                    continue

                attrs[name] = value

            for name in sorted(attrs):
                self.stdout.write(f"  {name}: {attrs[name]!r}")

        self.stdout.write("")

        # ------------------------------------------------------------------
        # Actual weekly slot distribution derived from AssignmentVariable.
        # This is authoritative for the generated CP-SAT variable domain.
        # ------------------------------------------------------------------
        self.stdout.write("ACTUAL ASSIGNMENT VARIABLE SLOT DISTRIBUTION")

        day_period_counts = Counter()

        for assignment in assignment_by_cp_index.values():
            day = getattr(assignment, "day", None)
            period_id = getattr(assignment, "period_id", None)

            if day is not None and period_id is not None:
                day_period_counts[(str(day), str(period_id))] += 1

        period_by_id = {
            str(period.id): period
            for period in problem.periods
        }

        for (day, period_id), count in sorted(
            day_period_counts.items(),
            key=lambda item: (
                item[0][0],
                period_by_id.get(item[0][1]).number
                if item[0][1] in period_by_id
                else 999,
            ),
        ):
            period = period_by_id.get(period_id)
            number = getattr(period, "number", "?")
            name = getattr(period, "name", "?")
            self.stdout.write(
                f"  {day} P{number} ({name}): {count} variables"
            )

        self.stdout.write("")

        # ------------------------------------------------------------------
        # Period 1 audit
        # ------------------------------------------------------------------
        period1 = next(
            (
                period
                for period in problem.periods
                if getattr(period, "number", None) == 1
            ),
            None,
        )

        if period1 is None:
            raise RuntimeError("Active Period 1 was not found.")

        period1_id = str(period1.id)

        period1_assignments = [
            assignment
            for assignment in assignment_by_cp_index.values()
            if str(getattr(assignment, "period_id", "")) == period1_id
        ]

        grade10_period1 = [
            assignment
            for assignment in period1_assignments
            if getattr(assignment, "instructional_group_id", None) in grade10_ids
        ]

        self.stdout.write(
            "INSTITUTIONAL RESERVATION — PERIOD 1 VARIABLE AUDIT"
        )
        self.stdout.write(
            f"  TOTAL PERIOD-1 VARIABLES: {len(period1_assignments)}"
        )
        self.stdout.write(
            f"  GRADE 10 PERIOD-1 VARIABLES: {len(grade10_period1)}"
        )

        by_day = Counter(
            str(getattr(assignment, "day", None))
            for assignment in period1_assignments
        )

        self.stdout.write("")
        self.stdout.write("  PERIOD-1 VARIABLES BY DAY")

        for day, count in sorted(by_day.items()):
            self.stdout.write(f"    {day!r}: {count}")

        by_group = Counter(
            str(getattr(assignment, "instructional_group_id", None))
            for assignment in grade10_period1
        )

        group_by_id = {
            str(group.id): group
            for group in problem.instructional_groups
        }

        self.stdout.write("")
        self.stdout.write("  PERIOD-1 GRADE 10 VARIABLES BY GROUP")

        for group_id, count in sorted(by_group.items()):
            group = group_by_id.get(group_id)
            code = getattr(group, "code", "?") if group else "?"
            self.stdout.write(
                f"    {code} ({group_id}): {count}"
            )

        self.stdout.write("")

        # ------------------------------------------------------------------
        # Identify the institutional constraint family.
        #
        # Do NOT use WhichOneof().  The OR-Tools ConstraintProto wrapper in
        # this installed version does not expose that protobuf API.
        #
        # Instead, inspect supported fields directly.
        # ------------------------------------------------------------------
        self.stdout.write("INSTITUTIONAL CONSTRAINT PROTO ANALYSIS")

        family_count = 160

        if len(proto.constraints) < family_count:
            raise RuntimeError(
                "Model contains fewer constraints than the expected "
                "institutional reservation family."
            )

        institutional_constraints = [
            proto.constraints[index]
            for index in range(family_count)
        ]

        self.stdout.write(
            f"  CONSTRAINTS: {len(institutional_constraints)}"
        )

        field_counts = Counter()

        for constraint in institutional_constraints:
            for field_name in (
                "linear",
                "bool_or",
                "bool_and",
                "all_diff",
                "element",
                "interval",
                "no_overlap",
                "cumulative",
                "automaton",
                "table",
            ):
                try:
                    value = getattr(constraint, field_name)
                except AttributeError:
                    continue

                if value is not None:
                    try:
                        has_content = len(value) > 0
                    except TypeError:
                        has_content = True

                    if has_content:
                        field_counts[field_name] += 1

        self.stdout.write("  SUPPORTED NON-EMPTY CONSTRAINT FIELDS")

        if field_counts:
            for field_name, count in sorted(field_counts.items()):
                self.stdout.write(
                    f"    {field_name}: {count}"
                )
        else:
            self.stdout.write("    NONE DETECTED")

        self.stdout.write("")

        # ------------------------------------------------------------------
        # Map institutional linear constraints to AssignmentVariables.
        # ------------------------------------------------------------------
        mapped_indices = []
        unmapped_indices = []

        for index, constraint in enumerate(institutional_constraints):
            linear = getattr(constraint, "linear", None)

            if linear is None:
                unmapped_indices.append(index)
                continue

            vars_field = getattr(linear, "vars", None)

            if vars_field is None:
                unmapped_indices.append(index)
                continue

            for raw_index in vars_field:
                cp_index = int(raw_index)

                if cp_index in assignment_by_cp_index:
                    mapped_indices.append(cp_index)
                else:
                    unmapped_indices.append(index)

        self.stdout.write(
            "  INSTITUTIONAL CONSTRAINT VARIABLE MAPPING"
        )
        self.stdout.write(
            f"    ASSIGNMENT VARIABLE REFERENCES: {len(mapped_indices)}"
        )
        self.stdout.write(
            f"    UNMAPPED CONSTRAINT REFERENCES: {len(unmapped_indices)}"
        )
        self.stdout.write("")

        mapped_assignments = [
            assignment_by_cp_index[index]
            for index in mapped_indices
            if index in assignment_by_cp_index
        ]

        mapped_by_day = Counter(
            str(getattr(assignment, "day", None))
            for assignment in mapped_assignments
        )

        self.stdout.write(
            "  INSTITUTIONAL CONSTRAINT REFERENCES BY DAY"
        )

        if mapped_by_day:
            for day, count in sorted(mapped_by_day.items()):
                self.stdout.write(f"    {day!r}: {count}")
        else:
            self.stdout.write("    NONE")

        mapped_by_period = Counter(
            str(getattr(assignment, "period_id", None))
            for assignment in mapped_assignments
        )

        self.stdout.write("")
        self.stdout.write(
            "  INSTITUTIONAL CONSTRAINT REFERENCES BY PERIOD"
        )

        for period_id, count in sorted(
            mapped_by_period.items(),
            key=lambda item: (
                period_by_id.get(item[0]).number
                if item[0] in period_by_id
                else 999
            ),
        ):
            period = period_by_id.get(period_id)
            number = getattr(period, "number", "?")
            name = getattr(period, "name", "?")
            self.stdout.write(
                f"    P{number} ({name}): {count}"
            )

        self.stdout.write("")

        mapped_grade10 = [
            assignment
            for assignment in mapped_assignments
            if getattr(assignment, "instructional_group_id", None)
            in grade10_ids
        ]

        self.stdout.write(
            "  INSTITUTIONAL CONSTRAINT REFERENCES — GRADE 10"
        )
        self.stdout.write(
            f"    GRADE 10 REFERENCES: {len(mapped_grade10)}"
        )

        grade10_by_day = Counter(
            str(getattr(assignment, "day", None))
            for assignment in mapped_grade10
        )

        for day, count in sorted(grade10_by_day.items()):
            self.stdout.write(
                f"    {day!r}: {count}"
            )

        self.stdout.write("")

        # ------------------------------------------------------------------
        # Exact production solve — read-only.
        # ------------------------------------------------------------------
        self.stdout.write("-" * 78)
        self.stdout.write("EXACT PRODUCTION SOLVER RECHECK")
        self.stdout.write("-" * 78)

        solver = CPSATSolver()

        result = solver.solve(
            problem,
            solver_model,
        )

        self.stdout.write(f"  STATUS:      {result.status}")
        self.stdout.write(f"  ASSIGNMENTS: {len(result.assignments)}")

        statistics = result.statistics

        self.stdout.write(
            f"  WALL TIME:   {getattr(statistics, 'wall_time_seconds', None)}"
        )
        self.stdout.write(
            f"  BRANCHES:    {getattr(statistics, 'branches', None)}"
        )
        self.stdout.write(
            f"  CONFLICTS:   {getattr(statistics, 'conflicts', None)}"
        )
        self.stdout.write(
            f"  OBJECTIVE:   {getattr(statistics, 'objective_value', None)}"
        )
        self.stdout.write(
            f"  ERROR:       {getattr(result, 'error_message', None)}"
        )

        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("CORE CONFLICT AUDIT COMPLETE")
        self.stdout.write("=" * 78)
