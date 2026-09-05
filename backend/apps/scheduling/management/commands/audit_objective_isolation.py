from django.core.management.base import BaseCommand

from apps.scheduling.models import SchedulingRun
from apps.scheduling.engine.infrastructure.django_loader import DjangoSchedulingLoader
from apps.scheduling.engine.solver.model import SolverModelBuilder
from apps.scheduling.engine.solver.solver import CPSATSolver


KNOWN_GOOD_RUN_ID = "8eccf5f8-c91a-439a-9970-297abfbdc403"
TIME_LIMIT_SECONDS = 120


class Command(BaseCommand):
    help = "Read-only production hard-constraint isolation audit."

    def handle(self, *args, **options):
        self.stdout.write("=" * 78)
        self.stdout.write("SMARTTIMETABLE HARD-CONSTRAINT ISOLATION AUDIT")
        self.stdout.write("=" * 78)
        self.stdout.write("READ-ONLY: YES")
        self.stdout.write("DATABASE MUTATION: NO")
        self.stdout.write("")

        run = SchedulingRun.objects.select_related("term").get(
            id=KNOWN_GOOD_RUN_ID
        )

        loader = DjangoSchedulingLoader()
        problem = loader.load_problem(term=run.term)

        self.stdout.write("PROBLEM")
        self.stdout.write(f"  REQUIREMENTS: {len(problem.lesson_requirements)}")
        self.stdout.write(f"  TEACHERS:     {len(problem.teachers)}")
        self.stdout.write(f"  GROUPS:       {len(problem.instructional_groups)}")
        self.stdout.write(f"  ROOMS:        {len(problem.rooms)}")
        self.stdout.write(f"  PERIODS:      {len(problem.periods)}")
        self.stdout.write(f"  SLOTS:        {len(problem.slots)}")
        self.stdout.write("")

        # ==============================================================
        # TEST 1 — EXACT PRODUCTION MODEL
        # ==============================================================

        self.stdout.write("-" * 78)
        self.stdout.write("TEST 1 — EXACT PRODUCTION MODEL")
        self.stdout.write("-" * 78)

        production_model = SolverModelBuilder().build(problem)

        production_has_objective = (
            production_model.model.has_objective()
        )

        self.stdout.write(
            f"  VARIABLES:     "
            f"{len(production_model.model.proto.variables)}"
        )
        self.stdout.write(
            f"  CONSTRAINTS:   "
            f"{len(production_model.model.proto.constraints)}"
        )
        self.stdout.write(
            f"  HAS OBJECTIVE: {production_has_objective}"
        )

        production_solver = CPSATSolver(
            time_limit_seconds=TIME_LIMIT_SECONDS,
            num_workers=None,
        )

        production_result = production_solver.solve(
            problem,
            production_model,
        )

        self.stdout.write(f"  STATUS:        {production_result.status}")
        self.stdout.write(
            f"  ASSIGNMENTS:   {len(production_result.assignments)}"
        )
        self.stdout.write(
            f"  WALL TIME:     "
            f"{production_result.statistics.wall_time_seconds}"
        )
        self.stdout.write(
            f"  BRANCHES:      {production_result.statistics.branches}"
        )
        self.stdout.write(
            f"  CONFLICTS:     {production_result.statistics.conflicts}"
        )
        self.stdout.write(
            f"  OBJECTIVE:     "
            f"{production_result.statistics.objective_value}"
        )
        self.stdout.write("")

        # ==============================================================
        # TEST 2 — EXPLICIT OBJECTIVE CLEAR
        #
        # This is deliberately a second independently built model.
        # The runtime API confirmed ClearObjective() is supported.
        # ==============================================================

        self.stdout.write("-" * 78)
        self.stdout.write("TEST 2 — EXPLICIT OBJECTIVE CLEAR")
        self.stdout.write("-" * 78)

        no_objective_model = SolverModelBuilder().build(problem)

        objective_before = no_objective_model.model.has_objective()

        self.stdout.write(
            f"  OBJECTIVE BEFORE: {objective_before}"
        )

        no_objective_model.model.ClearObjective()

        objective_after = no_objective_model.model.has_objective()

        self.stdout.write(
            f"  OBJECTIVE AFTER:  {objective_after}"
        )

        no_objective_solver = CPSATSolver(
            time_limit_seconds=TIME_LIMIT_SECONDS,
            num_workers=None,
        )

        no_objective_result = no_objective_solver.solve(
            problem,
            no_objective_model,
        )

        self.stdout.write(f"  STATUS:        {no_objective_result.status}")
        self.stdout.write(
            f"  ASSIGNMENTS:   {len(no_objective_result.assignments)}"
        )
        self.stdout.write(
            f"  WALL TIME:     "
            f"{no_objective_result.statistics.wall_time_seconds}"
        )
        self.stdout.write(
            f"  BRANCHES:      {no_objective_result.statistics.branches}"
        )
        self.stdout.write(
            f"  CONFLICTS:     {no_objective_result.statistics.conflicts}"
        )
        self.stdout.write(
            f"  OBJECTIVE:     "
            f"{no_objective_result.statistics.objective_value}"
        )
        self.stdout.write("")

        # ==============================================================
        # DECISION
        # ==============================================================

        production_status = str(production_result.status).upper()
        no_objective_status = str(no_objective_result.status).upper()

        self.stdout.write("=" * 78)
        self.stdout.write("HARD-CONSTRAINT ISOLATION DECISION")
        self.stdout.write("=" * 78)

        if "INFEASIBLE" in production_status:
            self.stdout.write(
                "PROVEN: PRODUCTION MODEL IS INFEASIBLE"
            )

        if not production_has_objective:
            self.stdout.write(
                "PROVEN: PRODUCTION MODEL CONTAINS NO OBJECTIVE"
            )
            self.stdout.write(
                "Therefore the current INFEASIBLE result is NOT caused"
            )
            self.stdout.write(
                "by BalancedTeacherWorkloadObjective or "
                "TeacherConsecutivePeriodObjective."
            )

        if (
            "INFEASIBLE" in production_status
            and "INFEASIBLE" in no_objective_status
        ):
            self.stdout.write("")
            self.stdout.write(
                "FINAL RESULT: HARD CONSTRAINT INFEASIBILITY PROVEN"
            )
            self.stdout.write(
                "The model remains INFEASIBLE after explicit objective "
                "removal."
            )

        elif (
            "INFEASIBLE" in production_status
            and (
                "OPTIMAL" in no_objective_status
                or "FEASIBLE" in no_objective_status
            )
        ):
            self.stdout.write("")
            self.stdout.write(
                "RESULT: OBJECTIVE-DEPENDENT BEHAVIOUR DETECTED"
            )
            self.stdout.write(
                "However, this would require the first model to have "
                "contained an objective."
            )

        else:
            self.stdout.write("")
            self.stdout.write(
                "RESULT: FURTHER ISOLATION REQUIRED"
            )

        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write("AUDIT COMPLETE")
        self.stdout.write("=" * 78)
