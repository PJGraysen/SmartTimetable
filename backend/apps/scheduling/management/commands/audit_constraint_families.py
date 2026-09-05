from django.core.management.base import BaseCommand

from apps.scheduling.models import SchedulingRun
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver


KNOWN_GOOD_RUN_ID = "8eccf5f8-c91a-439a-9970-297abfbdc403"
TIME_LIMIT_SECONDS = 30


CONSTRAINT_FAMILIES = (
    (
        "institutional_reserved",
        "_add_institutional_reserved_period_constraints",
    ),
    (
        "lesson_requirements",
        "_add_lesson_requirement_constraints",
    ),
    (
        "grade10_option_blocks",
        "_add_grade10_option_block_constraints",
    ),
    (
        "simultaneous_subjects",
        "_add_simultaneous_subject_constraints",
    ),
    (
        "teacher_clashes",
        "_add_teacher_clash_constraints",
    ),
    (
        "group_clashes",
        "_add_group_clash_constraints",
    ),
    (
        "single_lesson_per_day",
        "_add_single_lesson_per_day_constraints",
    ),
    (
        "room_clashes",
        "_add_room_clash_constraints",
    ),
    (
        "teacher_availability",
        "_add_teacher_availability_constraints",
    ),
    (
        "teacher_free_afternoons",
        "_add_teacher_free_afternoon_constraints",
    ),
    (
        "room_availability",
        "_add_room_availability_constraints",
    ),
)


class SelectiveSolverModelBuilder(SolverModelBuilder):
    """
    Production SolverModelBuilder with exactly one selected
    constraint-family method disabled.

    This subclass exists only inside this diagnostic command.
    Production model.py is not modified.
    """

    disabled_method = None

    def _disabled(self, method_name):
        return self.disabled_method == method_name

    def _add_institutional_reserved_period_constraints(
        self,
        *,
        model,
        problem,
        variables,
    ):
        if self._disabled(
            "_add_institutional_reserved_period_constraints"
        ):
            return

        return super()._add_institutional_reserved_period_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

    def _add_lesson_requirement_constraints(
        self,
        *,
        model,
        problem,
        variables,
    ):
        if self._disabled(
            "_add_lesson_requirement_constraints"
        ):
            return

        return super()._add_lesson_requirement_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

    def _add_grade10_option_block_constraints(
        self,
        *,
        model,
        problem,
        variables,
    ):
        if self._disabled(
            "_add_grade10_option_block_constraints"
        ):
            return

        return super()._add_grade10_option_block_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

    def _add_simultaneous_subject_constraints(
        self,
        *,
        model,
        problem,
        variables,
    ):
        if self._disabled(
            "_add_simultaneous_subject_constraints"
        ):
            return

        return super()._add_simultaneous_subject_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

    def _add_teacher_clash_constraints(
        self,
        *,
        model,
        variables,
    ):
        if self._disabled(
            "_add_teacher_clash_constraints"
        ):
            return

        return super()._add_teacher_clash_constraints(
            model=model,
            variables=variables,
        )

    def _add_group_clash_constraints(
        self,
        *,
        model,
        problem,
        variables,
    ):
        if self._disabled(
            "_add_group_clash_constraints"
        ):
            return

        return super()._add_group_clash_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

    def _add_single_lesson_per_day_constraints(
        self,
        *,
        model,
        problem,
        variables,
    ):
        if self._disabled(
            "_add_single_lesson_per_day_constraints"
        ):
            return

        return super()._add_single_lesson_per_day_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

    def _add_room_clash_constraints(
        self,
        *,
        model,
        variables,
    ):
        if self._disabled(
            "_add_room_clash_constraints"
        ):
            return

        return super()._add_room_clash_constraints(
            model=model,
            variables=variables,
        )

    def _add_teacher_availability_constraints(
        self,
        *,
        model,
        problem,
        variables,
    ):
        if self._disabled(
            "_add_teacher_availability_constraints"
        ):
            return

        return super()._add_teacher_availability_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

    def _add_teacher_free_afternoon_constraints(
        self,
        *,
        model,
        problem,
        variables,
    ):
        if self._disabled(
            "_add_teacher_free_afternoon_constraints"
        ):
            return

        return super()._add_teacher_free_afternoon_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )

    def _add_room_availability_constraints(
        self,
        *,
        model,
        problem,
        variables,
    ):
        if self._disabled(
            "_add_room_availability_constraints"
        ):
            return

        return super()._add_room_availability_constraints(
            model=model,
            problem=problem,
            variables=variables,
        )


class Command(BaseCommand):
    help = "Read-only isolation of individual production hard-constraint families."

    def solve_case(self, problem, disabled_method=None):
        builder = SelectiveSolverModelBuilder()
        builder.disabled_method = disabled_method

        solver_model = builder.build(problem)

        solver = CPSATSolver(
            time_limit_seconds=TIME_LIMIT_SECONDS,
            num_workers=None,
        )

        result = solver.solve(
            problem,
            solver_model,
        )

        return solver_model, result

    def handle(self, *args, **options):
        self.stdout.write("=" * 78)
        self.stdout.write(
            "SMARTTIMETABLE HARD-CONSTRAINT FAMILY ISOLATION"
        )
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: YES")
        self.stdout.write("DATABASE MUTATION: NO")
        self.stdout.write("PRODUCTION MODEL MODIFIED: NO")
        self.stdout.write(
            f"PER-TEST TIME LIMIT: {TIME_LIMIT_SECONDS} seconds"
        )
        self.stdout.write("")

        run = SchedulingRun.objects.select_related("term").get(
            id=KNOWN_GOOD_RUN_ID
        )

        problem = DjangoSchedulingLoader().load_problem(
            term=run.term
        )

        self.stdout.write("CURRENT PROBLEM")
        self.stdout.write(
            f"  REQUIREMENTS: {len(problem.lesson_requirements)}"
        )
        self.stdout.write(f"  TEACHERS:     {len(problem.teachers)}")
        self.stdout.write(
            f"  GROUPS:       {len(problem.instructional_groups)}"
        )
        self.stdout.write(f"  ROOMS:        {len(problem.rooms)}")
        self.stdout.write(f"  PERIODS:      {len(problem.periods)}")
        self.stdout.write(f"  SLOTS:        {len(problem.slots)}")
        self.stdout.write("")

        # --------------------------------------------------------------
        # BASELINE
        # --------------------------------------------------------------

        self.stdout.write("-" * 78)
        self.stdout.write("BASELINE — ALL HARD CONSTRAINTS")
        self.stdout.write("-" * 78)

        baseline_model, baseline_result = self.solve_case(
            problem
        )

        self.stdout.write(
            f"  VARIABLES:   "
            f"{len(baseline_model.model.proto.variables)}"
        )
        self.stdout.write(
            f"  CONSTRAINTS: "
            f"{len(baseline_model.model.proto.constraints)}"
        )
        self.stdout.write(
            f"  STATUS:      {baseline_result.status}"
        )
        self.stdout.write(
            f"  ASSIGNMENTS: {len(baseline_result.assignments)}"
        )
        self.stdout.write(
            f"  TIME:        "
            f"{baseline_result.statistics.wall_time_seconds}"
        )
        self.stdout.write("")

        # --------------------------------------------------------------
        # INDIVIDUAL FAMILY REMOVAL
        # --------------------------------------------------------------

        results = []

        for label, method_name in CONSTRAINT_FAMILIES:
            self.stdout.write("-" * 78)
            self.stdout.write(
                f"DISABLED FAMILY: {label}"
            )
            self.stdout.write("-" * 78)

            try:
                model, result = self.solve_case(
                    problem,
                    disabled_method=method_name,
                )

                status = str(result.status)

                self.stdout.write(
                    f"  VARIABLES:   "
                    f"{len(model.model.proto.variables)}"
                )
                self.stdout.write(
                    f"  CONSTRAINTS: "
                    f"{len(model.model.proto.constraints)}"
                )
                self.stdout.write(
                    f"  STATUS:      {status}"
                )
                self.stdout.write(
                    f"  ASSIGNMENTS: {len(result.assignments)}"
                )
                self.stdout.write(
                    f"  TIME:        "
                    f"{result.statistics.wall_time_seconds}"
                )
                self.stdout.write(
                    f"  BRANCHES:    "
                    f"{result.statistics.branches}"
                )
                self.stdout.write(
                    f"  CONFLICTS:   "
                    f"{result.statistics.conflicts}"
                )

                if (
                    "OPTIMAL" in status.upper()
                    or "FEASIBLE" in status.upper()
                ):
                    marker = "<<< FEASIBLE WHEN THIS FAMILY IS REMOVED"
                else:
                    marker = ""

                self.stdout.write(
                    f"  {marker}"
                )

                results.append(
                    (
                        label,
                        status,
                        len(result.assignments),
                        result.statistics.wall_time_seconds,
                    )
                )

            except Exception as exc:
                self.stdout.write(
                    f"  ERROR: {type(exc).__name__}: {exc}"
                )

                results.append(
                    (
                        label,
                        f"ERROR: {type(exc).__name__}",
                        0,
                        0,
                    )
                )

            self.stdout.write("")

        # --------------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------------

        self.stdout.write("=" * 78)
        self.stdout.write("ISOLATION SUMMARY")
        self.stdout.write("=" * 78)

        feasible_cases = []

        for label, status, assignments, wall_time in results:
            if (
                "OPTIMAL" in status.upper()
                or "FEASIBLE" in status.upper()
            ):
                feasible_cases.append(label)

            self.stdout.write(
                f"{label:<32} {status:<24} "
                f"assignments={assignments:<5} "
                f"time={wall_time}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 78)

        if feasible_cases:
            self.stdout.write(
                "IMPORTANT: ONE OR MORE CONSTRAINT FAMILIES "
                "ISOLATED THE INFEASIBILITY."
            )
            self.stdout.write("")
            self.stdout.write("FEASIBLE WHEN DISABLED:")
            for label in feasible_cases:
                self.stdout.write(f"  >>> {label}")
            self.stdout.write("")
            self.stdout.write(
                "This identifies candidate constraint families."
            )
            self.stdout.write(
                "It does NOT authorize removing the constraint."
            )
        else:
            self.stdout.write(
                "NO SINGLE CONSTRAINT FAMILY REMOVAL PRODUCED "
                "A FEASIBLE MODEL."
            )
            self.stdout.write("")
            self.stdout.write(
                "The contradiction is therefore likely an interaction "
                "between two or more hard-constraint families."
            )

        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("AUDIT COMPLETE")
        self.stdout.write("=" * 78)
