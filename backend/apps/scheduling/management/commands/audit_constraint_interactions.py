from django.core.management.base import BaseCommand

from apps.scheduling.models import SchedulingRun
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver


KNOWN_GOOD_RUN_ID = "8eccf5f8-c91a-439a-9970-297abfbdc403"
TIME_LIMIT_SECONDS = 30


FAMILIES = {
    "institutional_reserved":
        "_add_institutional_reserved_period_constraints",

    "lesson_requirements":
        "_add_lesson_requirement_constraints",

    "grade10_option_blocks":
        "_add_grade10_option_block_constraints",

    "simultaneous_subjects":
        "_add_simultaneous_subject_constraints",

    "teacher_clashes":
        "_add_teacher_clash_constraints",

    "group_clashes":
        "_add_group_clash_constraints",

    "single_lesson_per_day":
        "_add_single_lesson_per_day_constraints",

    "room_clashes":
        "_add_room_clash_constraints",

    "teacher_availability":
        "_add_teacher_availability_constraints",

    "teacher_free_afternoons":
        "_add_teacher_free_afternoon_constraints",

    "room_availability":
        "_add_room_availability_constraints",
}


class SelectiveSolverModelBuilder(SolverModelBuilder):
    disabled_methods = set()

    def _disabled(self, name):
        return name in self.disabled_methods

    def _add_institutional_reserved_period_constraints(
        self, *, model, problem, variables
    ):
        if not self._disabled(
            "_add_institutional_reserved_period_constraints"
        ):
            return super()._add_institutional_reserved_period_constraints(
                model=model,
                problem=problem,
                variables=variables,
            )

    def _add_lesson_requirement_constraints(
        self, *, model, problem, variables
    ):
        if not self._disabled(
            "_add_lesson_requirement_constraints"
        ):
            return super()._add_lesson_requirement_constraints(
                model=model,
                problem=problem,
                variables=variables,
            )

    def _add_grade10_option_block_constraints(
        self, *, model, problem, variables
    ):
        if not self._disabled(
            "_add_grade10_option_block_constraints"
        ):
            return super()._add_grade10_option_block_constraints(
                model=model,
                problem=problem,
                variables=variables,
            )

    def _add_simultaneous_subject_constraints(
        self, *, model, problem, variables
    ):
        if not self._disabled(
            "_add_simultaneous_subject_constraints"
        ):
            return super()._add_simultaneous_subject_constraints(
                model=model,
                problem=problem,
                variables=variables,
            )

    def _add_teacher_clash_constraints(
        self, *, model, variables
    ):
        if not self._disabled(
            "_add_teacher_clash_constraints"
        ):
            return super()._add_teacher_clash_constraints(
                model=model,
                variables=variables,
            )

    def _add_group_clash_constraints(
        self, *, model, problem, variables
    ):
        if not self._disabled(
            "_add_group_clash_constraints"
        ):
            return super()._add_group_clash_constraints(
                model=model,
                problem=problem,
                variables=variables,
            )

    def _add_single_lesson_per_day_constraints(
        self, *, model, problem, variables
    ):
        if not self._disabled(
            "_add_single_lesson_per_day_constraints"
        ):
            return super()._add_single_lesson_per_day_constraints(
                model=model,
                problem=problem,
                variables=variables,
            )

    def _add_room_clash_constraints(
        self, *, model, variables
    ):
        if not self._disabled(
            "_add_room_clash_constraints"
        ):
            return super()._add_room_clash_constraints(
                model=model,
                variables=variables,
            )

    def _add_teacher_availability_constraints(
        self, *, model, problem, variables
    ):
        if not self._disabled(
            "_add_teacher_availability_constraints"
        ):
            return super()._add_teacher_availability_constraints(
                model=model,
                problem=problem,
                variables=variables,
            )

    def _add_teacher_free_afternoon_constraints(
        self, *, model, problem, variables
    ):
        if not self._disabled(
            "_add_teacher_free_afternoon_constraints"
        ):
            return super()._add_teacher_free_afternoon_constraints(
                model=model,
                problem=problem,
                variables=variables,
            )

    def _add_room_availability_constraints(
        self, *, model, problem, variables
    ):
        if not self._disabled(
            "_add_room_availability_constraints"
        ):
            return super()._add_room_availability_constraints(
                model=model,
                problem=problem,
                variables=variables,
            )


class Command(BaseCommand):
    help = "Read-only pairwise hard-constraint interaction audit."

    def solve(self, problem, disabled_names):
        disabled_methods = {
            FAMILIES[name]
            for name in disabled_names
        }

        builder = SelectiveSolverModelBuilder()
        builder.disabled_methods = disabled_methods

        model = builder.build(problem)

        solver = CPSATSolver(
            time_limit_seconds=TIME_LIMIT_SECONDS,
            num_workers=None,
        )

        result = solver.solve(problem, model)

        return model, result

    def handle(self, *args, **options):
        self.stdout.write("=" * 78)
        self.stdout.write(
            "SMARTTIMETABLE HARD-CONSTRAINT INTERACTION AUDIT"
        )
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: YES")
        self.stdout.write("DATABASE MUTATION: NO")
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

        self.stdout.write("PROBLEM")
        self.stdout.write(
            f"  REQUIREMENTS: {len(problem.lesson_requirements)}"
        )
        self.stdout.write(
            f"  TEACHERS:     {len(problem.teachers)}"
        )
        self.stdout.write(
            f"  GROUPS:       {len(problem.instructional_groups)}"
        )
        self.stdout.write(
            f"  ROOMS:        {len(problem.rooms)}"
        )
        self.stdout.write(
            f"  PERIODS:      {len(problem.periods)}"
        )
        self.stdout.write(
            f"  SLOTS:        {len(problem.slots)}"
        )
        self.stdout.write("")

        # These are the families that individually restored
        # feasibility in the previous audit.
        candidate_families = [
            "institutional_reserved",
            "lesson_requirements",
            "group_clashes",
        ]

        self.stdout.write("-" * 78)
        self.stdout.write(
            "PHASE 1 — PAIRS AMONG PRIMARY CANDIDATES"
        )
        self.stdout.write("-" * 78)

        feasible_pairs = []

        for index, first in enumerate(candidate_families):
            for second in candidate_families[index + 1:]:
                disabled = {first, second}

                self.stdout.write(
                    f"TEST: disable {first} + {second}"
                )

                try:
                    model, result = self.solve(
                        problem,
                        disabled,
                    )

                    status = str(result.status)

                    self.stdout.write(
                        f"  CONSTRAINTS: "
                        f"{len(model.model.proto.constraints)}"
                    )
                    self.stdout.write(
                        f"  STATUS: {status}"
                    )
                    self.stdout.write(
                        f"  ASSIGNMENTS: "
                        f"{len(result.assignments)}"
                    )
                    self.stdout.write(
                        f"  TIME: "
                        f"{result.statistics.wall_time_seconds}"
                    )

                    if (
                        "OPTIMAL" in status.upper()
                        or "FEASIBLE" in status.upper()
                    ):
                        feasible_pairs.append(
                            (first, second)
                        )
                        self.stdout.write(
                            "  >>> FEASIBLE"
                        )

                except Exception as exc:
                    self.stdout.write(
                        f"  ERROR: {type(exc).__name__}: {exc}"
                    )

                self.stdout.write("")

        # --------------------------------------------------------------
        # Phase 2: each primary candidate paired with every other
        # family. This catches interactions such as
        # lesson_requirements + teacher_clashes.
        # --------------------------------------------------------------

        self.stdout.write("-" * 78)
        self.stdout.write(
            "PHASE 2 — PRIMARY CANDIDATE × ALL OTHER FAMILIES"
        )
        self.stdout.write("-" * 78)

        tested = set(feasible_pairs)

        for primary in candidate_families:
            for other in FAMILIES:
                if primary == other:
                    continue

                pair = tuple(sorted((primary, other)))

                if pair in tested:
                    continue

                tested.add(pair)

                disabled = {primary, other}

                self.stdout.write(
                    f"TEST: disable {primary} + {other}"
                )

                try:
                    model, result = self.solve(
                        problem,
                        disabled,
                    )

                    status = str(result.status)

                    self.stdout.write(
                        f"  STATUS: {status}"
                    )
                    self.stdout.write(
                        f"  ASSIGNMENTS: "
                        f"{len(result.assignments)}"
                    )
                    self.stdout.write(
                        f"  TIME: "
                        f"{result.statistics.wall_time_seconds}"
                    )

                    if (
                        "OPTIMAL" in status.upper()
                        or "FEASIBLE" in status.upper()
                    ):
                        feasible_pairs.append(
                            (primary, other)
                        )
                        self.stdout.write(
                            "  >>> FEASIBLE WHEN BOTH ARE DISABLED"
                        )

                except Exception as exc:
                    self.stdout.write(
                        f"  ERROR: {type(exc).__name__}: {exc}"
                    )

                self.stdout.write("")

        # --------------------------------------------------------------
        # Final summary
        # --------------------------------------------------------------

        self.stdout.write("=" * 78)
        self.stdout.write("INTERACTION AUDIT SUMMARY")
        self.stdout.write("=" * 78)

        unique_pairs = []

        for pair in feasible_pairs:
            normalized = tuple(sorted(pair))
            if normalized not in unique_pairs:
                unique_pairs.append(normalized)

        if unique_pairs:
            self.stdout.write(
                "PAIRS THAT RESTORE FEASIBILITY:"
            )

            for first, second in unique_pairs:
                self.stdout.write(
                    f"  >>> {first} + {second}"
                )

            self.stdout.write("")
            self.stdout.write(
                "These are evidence-based candidate interactions."
            )
            self.stdout.write(
                "They do NOT authorize removing either constraint."
            )

        else:
            self.stdout.write(
                "NO TESTED PAIR RESTORED FEASIBILITY."
            )
            self.stdout.write("")
            self.stdout.write(
                "The contradiction likely requires three or more"
            )
            self.stdout.write(
                "constraint families interacting."
            )

        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("AUDIT COMPLETE")
        self.stdout.write("=" * 78)
