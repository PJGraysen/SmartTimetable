from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from ortools.sat.python import cp_model

from apps.academics.models import (
    InstructionalGroup,
    LessonRequirement,
)
from apps.users.models import Teacher

from apps.scheduling.models import (
    SchedulingRun,
)

from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)

from apps.scheduling.engine.solver.model import (
    SolverModelBuilder,
)


class Command(BaseCommand):
    help = "Read-only production generation dimension comparison."

    def handle(self, *args, **options):
        print("=" * 110)
        print("SMARTTIMETABLE PRO - GENERATION DIMENSION COMPARISON")
        print("=" * 110)
        print("READ-ONLY: NO DATABASE CHANGES")
        print()

        # ================================================================
        # REFERENCE RUN
        # ================================================================

        run = (
            SchedulingRun.objects
            .filter(status="COMPLETED")
            .select_related("term", "timetable_version")
            .order_by("-completed_at")
            .first()
        )

        if run is None:
            raise RuntimeError("No completed scheduling run found.")

        term = run.term

        print("1. REFERENCE COMPLETED RUN")
        print("-" * 110)
        print(f"RUN:           {run.id}")
        print(f"STATUS:        {run.status}")
        print(f"SOLVER STATUS: {run.solver_status}")
        print(f"STARTED:       {run.started_at}")
        print(f"COMPLETED:     {run.completed_at}")
        print(f"OBJECTIVE:     {run.objective_value}")
        print(f"VERSION:       {run.timetable_version}")
        print()

        # ================================================================
        # DATABASE INPUT
        # ================================================================

        requirements = list(
            LessonRequirement.objects
            .filter(
                term=term,
                is_active=True,
            )
            .select_related(
                "subject",
                "instructional_group",
            )
            .order_by(
                "instructional_group_id",
                "subject_id",
                "id",
            )
        )

        teachers = list(
            Teacher.objects
            .filter(is_active=True)
            .order_by("employee_code", "id")
        )

        groups = list(
            InstructionalGroup.objects
            .filter(
                teaching_group__stream__grade__academic_year=term.academic_year,
                is_active=True,
            )
            .select_related(
                "teaching_group",
                "teaching_group__stream",
                "teaching_group__stream__grade",
            )
            .order_by("code", "id")
        )

        print("2. CURRENT DATABASE INPUT")
        print("-" * 110)
        print(f"REQUIREMENTS: {len(requirements)}")
        print(f"TEACHERS:     {len(teachers)}")
        print(f"GROUPS:       {len(groups)}")
        print()

        # ================================================================
        # DOMAIN INPUT
        # ================================================================

        problem = DjangoSchedulingLoader().load_problem(term=term)

        print("3. CURRENT PRODUCTION DOMAIN")
        print("-" * 110)
        print(f"REQUIREMENTS:         {len(problem.lesson_requirements)}")
        print(f"TEACHERS:             {len(problem.teachers)}")
        print(f"GROUPS:               {len(problem.instructional_groups)}")
        print(f"ROOMS:                {len(problem.rooms)}")
        print(f"PERIODS:              {len(problem.periods)}")
        print(f"SLOTS:                {len(problem.slots)}")
        print(f"TEACHER ASSIGNMENTS:  {len(problem.teacher_assignments)}")
        print(f"TEACHER AVAILABILITY: {len(problem.teacher_availability)}")
        print(f"FREE AFTERNOONS:      {len(problem.teacher_free_afternoons)}")
        print(f"ROOM AVAILABILITY:    {len(problem.room_availability)}")
        print()

        # ================================================================
        # DOMAIN LOOKUPS
        # ================================================================

        domain_requirements = {
            requirement.id: requirement
            for requirement in problem.lesson_requirements
        }

        domain_teachers = {
            teacher.id: teacher
            for teacher in problem.teachers
        }

        domain_groups = {
            group.id: group
            for group in problem.instructional_groups
        }

        # ================================================================
        # TEACHER ASSIGNMENTS
        #
        # TeacherAssignmentEntity fields are:
        #   id
        #   lesson_requirement_id
        #   teacher_id
        #   is_active
        # ================================================================

        assignments_by_requirement = defaultdict(list)

        print("4. TEACHER ASSIGNMENT ANALYSIS")
        print("-" * 110)

        valid_assignments = 0
        invalid_requirement_refs = 0
        invalid_teacher_refs = 0

        for assignment in problem.teacher_assignments:
            if not assignment.is_active:
                continue

            requirement_id = assignment.lesson_requirement_id
            teacher_id = assignment.teacher_id

            requirement = domain_requirements.get(requirement_id)
            teacher = domain_teachers.get(teacher_id)

            if requirement is None:
                invalid_requirement_refs += 1

            if teacher is None:
                invalid_teacher_refs += 1

            if requirement is not None and teacher is not None:
                assignments_by_requirement[
                    requirement_id
                ].append(teacher_id)

                valid_assignments += 1

            subject_code = "UNKNOWN"
            group_code = "UNKNOWN"

            if requirement is not None:
                subject = next(
                    (
                        item
                        for item in requirements
                        if item.id == requirement_id
                    ),
                    None,
                )

                if subject is not None:
                    subject_code = (
                        getattr(subject.subject, "code", None)
                        or str(subject.subject_id)
                    )

                group = domain_groups.get(
                    requirement.instructional_group_id
                )

                if group is not None:
                    group_code = group.code

            teacher_code = "UNKNOWN"

            if teacher is not None:
                teacher_code = teacher.code

            print(
                f"REQ={requirement_id} | "
                f"GROUP={group_code} | "
                f"SUBJECT={subject_code} | "
                f"TEACHER={teacher_code} | "
                f"TEACHER_ID={teacher_id}"
            )

        print()
        print(f"VALID ASSIGNMENTS:             {valid_assignments}")
        print(f"INVALID REQUIREMENT REFERENCES:{invalid_requirement_refs}")
        print(f"INVALID TEACHER REFERENCES:    {invalid_teacher_refs}")
        print()

        # ================================================================
        # EXACT PRODUCTION VARIABLE CREATION
        # ================================================================

        model = cp_model.CpModel()

        builder = SolverModelBuilder()

        variables = builder._create_assignment_variables(
            model=model,
            problem=problem,
        )

        print("5. RAW PRODUCTION VARIABLES")
        print("-" * 110)
        print(f"VARIABLES CREATED: {len(variables)}")
        print()

        variables_by_requirement = defaultdict(list)

        for variable in variables:
            variables_by_requirement[
                variable.lesson_requirement_id
            ].append(variable)

        # ================================================================
        # PER REQUIREMENT AUDIT
        # ================================================================

        print("6. PER-REQUIREMENT VARIABLE AUDIT")
        print("-" * 110)

        expected_total = 0
        actual_total = 0
        mismatches = 0

        for requirement in problem.lesson_requirements:
            requirement_id = requirement.id

            assigned_teachers = sorted(
                set(
                    assignments_by_requirement.get(
                        requirement_id,
                        [],
                    )
                ),
                key=str,
            )

            # This mirrors the intended variable-domain rule:
            #
            # assigned teachers -> one variable domain per assigned teacher
            # no assignment     -> teacherless variable
            #
            teacher_option_count = (
                len(assigned_teachers)
                if assigned_teachers
                else 1
            )

            expected_count = (
                teacher_option_count
                * len(problem.slots)
                * len(problem.rooms)
            )

            actual_variables = variables_by_requirement.get(
                requirement_id,
                [],
            )

            actual_count = len(actual_variables)

            expected_total += expected_count
            actual_total += actual_count

            actual_teacher_ids = sorted(
                {
                    variable.teacher_id
                    for variable in actual_variables
                },
                key=lambda value: str(value),
            )

            actual_teacher_codes = []

            for teacher_id in actual_teacher_ids:
                if teacher_id is None:
                    actual_teacher_codes.append("NO_TEACHER")
                else:
                    teacher = domain_teachers.get(teacher_id)

                    if teacher is None:
                        actual_teacher_codes.append(
                            f"UNKNOWN:{teacher_id}"
                        )
                    else:
                        actual_teacher_codes.append(
                            teacher.code
                        )

            db_requirement = next(
                (
                    item
                    for item in requirements
                    if item.id == requirement_id
                ),
                None,
            )

            subject_code = "UNKNOWN"

            if db_requirement is not None:
                subject_code = (
                    getattr(
                        db_requirement.subject,
                        "code",
                        None,
                    )
                    or str(db_requirement.subject_id)
                )

            group = domain_groups.get(
                requirement.instructional_group_id
            )

            group_code = (
                group.code
                if group is not None
                else str(requirement.instructional_group_id)
            )

            mismatch = actual_count != expected_count

            if mismatch:
                mismatches += 1

            print(
                f"{'MISMATCH' if mismatch else 'OK':8} | "
                f"{group_code:5} | "
                f"{subject_code:8} | "
                f"WEEK={requirement.periods_per_week:2} | "
                f"ASSIGNED={len(assigned_teachers):2} | "
                f"ACTUAL_TEACHERS="
                f"{','.join(actual_teacher_codes) or '<NONE>'} | "
                f"EXPECTED={expected_count:5} | "
                f"ACTUAL={actual_count:5}"
            )

        print()

        # ================================================================
        # MODEL SIZE
        # ================================================================

        print("7. MODEL DIMENSION")
        print("-" * 110)

        proto = model.proto

        print(f"MODEL VARIABLES:   {len(proto.variables)}")
        print(f"MODEL CONSTRAINTS: {len(proto.constraints)}")
        print(f"HAS OBJECTIVE:     {bool(proto.objective)}")
        print()

        # ================================================================
        # RECONCILIATION
        # ================================================================

        print("8. RECONCILIATION")
        print("-" * 110)

        print(f"EXPECTED VARIABLES: {expected_total}")
        print(f"ACTUAL VARIABLES:   {actual_total}")
        print(f"MISMATCHED REQS:    {mismatches}")
        print()

        if mismatches == 0:
            print(
                "RESULT: PASS - variable dimensions match "
                "teacher-assignment domains."
            )
        else:
            print(
                "RESULT: FAIL - variable dimensions differ from "
                "teacher-assignment domains."
            )

        print()

        if actual_total == 7840:
            print(
                "NOTE: 7,840 = 40 requirements × 49 slots × 4 rooms."
            )

        print()
        print("=" * 110)
        print("READ-ONLY: NO DATABASE CHANGES")
        print("=" * 110)
