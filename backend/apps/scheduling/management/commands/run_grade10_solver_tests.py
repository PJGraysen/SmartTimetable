from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


SOLVER_TEST_FILES = (
    "scheduling/engine/solver/test_solver_constraints.py",
    "scheduling/engine/solver/test_solver_integration.py",
    "scheduling/engine/solver/test_solver_objective.py",
    "scheduling/engine/solver/test_objective.py",
    "scheduling/engine/solver/test_composite_objective.py",
    "scheduling/engine/solver/test_infeasibility_diagnostics.py",
    "scheduling/engine/solver/test_teacher_consecutive_objective.py",
)


class Command(BaseCommand):
    help = "Run SmartTimetable Pro Grade 10 solver tests using pytest."

    def handle(self, *args, **options):
        self.stdout.write("=" * 68)
        self.stdout.write("SMARTTIMETABLE PRO - GRADE 10 SOLVER TESTS")
        self.stdout.write("=" * 68)

        try:
            import pytest
        except ImportError as exc:
            raise CommandError(
                "pytest is not installed in the active virtual environment."
            ) from exc

        backend_root = Path(settings.BASE_DIR).resolve()
        tests_root = backend_root / "tests"
        solver_tests_root = tests_root / "scheduling" / "engine" / "solver"

        self.stdout.write("")
        self.stdout.write(f"BACKEND ROOT: {backend_root}")
        self.stdout.write(f"TEST ROOT:    {tests_root}")
        self.stdout.write("")

        if not tests_root.is_dir():
            raise CommandError(
                f"Tests directory does not exist: {tests_root}"
            )

        self.stdout.write("=== VERIFYING SOLVER TEST FILES ===")

        test_files = []

        for relative_path in SOLVER_TEST_FILES:
            test_path = tests_root / relative_path

            if test_path.is_file():
                test_files.append(str(test_path))
                self.stdout.write(f"  PASS - {relative_path}")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  MISSING - {relative_path}"
                    )
                )

        if not test_files:
            raise CommandError(
                f"No solver test files found under: {solver_tests_root}"
            )

        self.stdout.write("")
        self.stdout.write(
            f"FOUND {len(test_files)} / {len(SOLVER_TEST_FILES)} solver test files."
        )

        self.stdout.write("")
        self.stdout.write("=== PYTEST COLLECTION / EXECUTION ===")

        pytest_args = [
            "-ra",
            "-vv",
            "-s",
            *test_files,
        ]

        exit_code = pytest.main(pytest_args)

        self.stdout.write("")
        self.stdout.write("=" * 68)

        if exit_code == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "GRADE 10 SOLVER TESTS PASSED."
                )
            )
            self.stdout.write("=" * 68)
            return

        raise CommandError(
            f"Grade 10 solver tests failed with pytest exit code {exit_code}."
        )
