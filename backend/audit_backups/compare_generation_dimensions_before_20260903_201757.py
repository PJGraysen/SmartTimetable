from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from ortools.sat.python import cp_model

from apps.academics.models import LessonRequirement, Teacher, InstructionalGroup
from apps.scheduling.models import SchedulingRun
from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)
from apps.scheduling.engine.solver.model import SolverModelBuilder


def entity_value(obj, *names, default=None):
    """
    Safely retrieve a value from a domain entity/dataclass/object.
    """
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return default


def teacher_label(teacher):
    if teacher is None:
        return "<NO TEACHER>"

    code = entity_value(
        teacher,
        "code",
        "employee_code",
        "teacher_code",
        default=None,
    )

    name = entity_value(
        teacher,
        "name",
        "full_name",
        default=None,
    )

    if code and name:
        return f"{code} ({name})"

    if code:
        return str(code)

    if name:
        return str(name)

    return str(entity_value(teacher, "id", default="<UNKNOWN>"))


def group_label(group):
    if group is None:
        return "<NO GROUP>"

    code = entity_value(
        group,
        "code",
        "group_code",
        default=None,
    )

    name = entity_value(
        group,
        "name",
        "group_name",
        default=None,
    )

    if code and name:
        return f"{code} ({name})"

    if code:
        return str(code)

    if name:
        return str(name)

    return str(entity_value(group, "id", default="<UNKNOWN>"))


def subject_label(requirement):
    code = entity_value(
        requirement,
        "subject_code",
        default=None,
    )

    if code:
        return str(code)

    subject = entity_value(
        requirement,
        "subject",
        default=None,
    )

    if subject is not None:
        subject_code = entity_value(
            subject,
            "code",
            "subject_code",
            default=None,
        )

        if subject_code:
            return str(subject_code)

        subject_name = entity_value(
            subject,
            "name",
            "subject_name",
            default=None,
        )

        if subject_name:
            return str(subject_name)

    return str(
        entity_value(
            requirement,
            "subject_id",
            default="<UNKNOWN SUBJECT>",
        )
    )


class Command(BaseCommand):
    help = (
        "Read-only comparison of current production generation "
        "dimensions, teacher assignments and solver variables."
    )

    def handle(self, *args, **options):
        print("=" * 110)
        print("SMARTTIMETABLE PRO - GENERATION DIMENSION COMPARISON")
        print("=" * 110)
        print("READ-ONLY: NO DATABASE CHANGES")
        print()

        # ------------------------------------------------------------------
        # 1. REFERENCE RUN / TERM
        # ------------------------------------------------------------------

        latest_completed = (
            SchedulingRun.objects
            .filter(status="COMPLETED")
            .select_related("term", "timetable_version")
            .order_by("-completed_at")
            .first()
        )

        if latest_completed is None:
            raise RuntimeError("No completed scheduling run exists.")

        term = latest_completed.term

        print("1. REFERENCE COMPLETED RUN")
        print("-" * 110)
        print(f"RUN:          {latest_completed.id}")
        print(f"STATUS:       {latest_completed.status}")
        print(f"SOLVER:       {latest_completed.solver_status}")
        print(f"STARTED:      {latest_completed.started_at}")
        print(f"COMPLETED:    {latest_completed.completed_at}")
        print(f"OBJECTIVE:    {latest_completed.objective_value}")
        print(f"TERM:         {term}")
        print(f"TERM ID:      {term.id}")
        print()

        # ------------------------------------------------------------------
        # 2. DATABASE DIMENSIONS
        # ------------------------------------------------------------------

        db_requirements = list(
            LessonRequirement.objects
            .filter(term=term, is_active=True)
            .select_related("subject", "instructional_group")
            .order_by("instructional_group_id", "subject_id", "id")
        )

        db_teachers = list(
            Teacher.objects
            .filter(is_active=True)
            .order_by("employee_code", "id")
        )

        db_groups = list(
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

        print("2. CURRENT DATABASE DIMENSIONS")
        print("-" * 110)
        print(f"REQUIREMENTS: {len(db_requirements)}")
        print(f"TEACHERS:     {len(db_teachers)}")
        print(f"GROUPS:       {len(db_groups)}")
        print()

        # ------------------------------------------------------------------
        # 3. LOAD ACTUAL PRODUCTION DOMAIN
        # ------------------------------------------------------------------

        problem = DjangoSchedulingLoader().load_problem(term=term)

        print("3. CURRENT PRODUCTION DOMAIN")
        print("-" * 110)
        print(f"REQUIREMENTS:         {len(problem.lesson_requirements)}")
        print(f"TEACHERS:             {len(problem.teachers)}")
        print(f"INSTRUCTIONAL GROUPS: {len(problem.instructional_groups)}")
        print(f"ROOMS:                {len(problem.rooms)}")
        print(f"PERIODS:              {len(problem.periods)}")
        print(f"SLOTS:                {len(problem.slots)}")
        print(f"TEACHER ASSIGNMENTS:  {len(problem.teacher_assignments)}")
        print(f"TEACHER AVAILABILITY: {len(problem.teacher_availability)}")
        print(f"FREE AFTERNOONS:      {len(problem.teacher_free_afternoons)}")
        print(f"ROOM AVAILABILITY:    {len(problem.room_availability)}")
        print()

        # ------------------------------------------------------------------
        # 4. DOMAIN GROUPS
        # ------------------------------------------------------------------

        print("4. LOADED INSTRUCTIONAL GROUPS")
        print("-" * 110)

        domain_groups = {
            entity_value(group, "id"): group
            for group in problem.instructional_groups
        }

        for group in problem.instructional_groups:
            print(
                f"{group_label(group)} | "
                f"id={entity_value(group, 'id', default='<UNKNOWN>')}"
            )

        print()

        # ------------------------------------------------------------------
        # 5. DOMAIN TEACHERS
        # ------------------------------------------------------------------

        domain_teachers = {
            entity_value(teacher, "id"): teacher
            for teacher in problem.teachers
        }

        print("5. LOADED TEACHERS")
        print("-" * 110)

        for teacher in problem.teachers:
            print(
                f"{teacher_label(teacher)} | "
                f"id={entity_value(teacher, 'id', default='<UNKNOWN>')}"
            )

        print()

        # ------------------------------------------------------------------
        # 6. TEACHER ASSIGNMENTS
        # ------------------------------------------------------------------

        assignments_by_requirement = defaultdict(list)

        print("6. TEACHER ASSIGNMENTS")
        print("-" * 110)

        valid_assignment_count = 0
        invalid_requirement_count = 0
        invalid_teacher_count = 0

        for assignment in problem.teacher_assignments:
            if not entity_value(assignment, "is_active", default=True):
                continue

            assignment_id = entity_value(
                assignment,
                "id",
                default="<NO ID>",
            )

            requirement_id = entity_value(
                assignment,
                "lesson_requirement_id",
                default=None,
            )

            teacher_id = entity_value(
                assignment,
                "teacher_id",
                default=None,
            )

            # Some entity implementations may expose object references.
            if requirement_id is None:
                requirement = entity_value(
                    assignment,
                    "lesson_requirement",
                    default=None,
                )
                requirement_id = entity_value(
                    requirement,
                    "id",
                    default=None,
                )

            if teacher_id is None:
                teacher = entity_value(
                    assignment,
                    "teacher",
                    default=None,
                )
                teacher_id = entity_value(
                    teacher,
                    "id",
                    default=None,
                )

            requirement = next(
                (
                    r
                    for r in problem.lesson_requirements
                    if entity_value(r, "id") == requirement_id
                ),
                None,
            )

            teacher = domain_teachers.get(teacher_id)

            if requirement is None:
                invalid_requirement_count += 1
            elif teacher is None:
                invalid_teacher_count += 1
            else:
                valid_assignment_count += 1

            if requirement is not None and teacher is not None:
                assignments_by_requirement[requirement_id].append(
                    teacher_id
                )

            print(
                f"{assignment_id} | "
                f"REQ={requirement_id} | "
                f"SUBJECT={subject_label(requirement) if requirement else '<UNKNOWN>'} | "
                f"TEACHER={teacher_label(teacher)}"
            )

        print()
        print(f"VALID ASSIGNMENTS:            {valid_assignment_count}")
        print(f"INVALID REQUIREMENT REFERENCES:{invalid_requirement_count}")
        print(f"INVALID TEACHER REFERENCES:    {invalid_teacher_count}")
        print()

        # ------------------------------------------------------------------
        # 7. CREATE ONLY THE PRODUCTION VARIABLE SET
        # ------------------------------------------------------------------

        model = cp_model.CpModel()
        builder = SolverModelBuilder()

        variables = builder._create_assignment_variables(
            model=model,
            problem=problem,
        )

        print("7. RAW PRODUCTION ASSIGNMENT VARIABLES")
        print("-" * 110)
        print(f"VARIABLES GENERATED: {len(variables)}")
        print()

        variables_by_requirement = defaultdict(list)

        for variable in variables:
            requirement_id = entity_value(
                variable,
                "lesson_requirement_id",
                default=None,
            )

            variables_by_requirement[requirement_id].append(variable)

        # ------------------------------------------------------------------
        # 8. EXACT PER-REQUIREMENT DIMENSION AUDIT
        # ------------------------------------------------------------------

        print("8. PER-REQUIREMENT VARIABLE AUDIT")
        print("-" * 110)

        expected_total = 0
        actual_total = 0
        mismatches = 0

        for requirement in problem.lesson_requirements:
            requirement_id = entity_value(requirement, "id")
            group_id = entity_value(
                requirement,
                "instructional_group_id",
                default=None,
            )

            group = domain_groups.get(group_id)

            assigned_teacher_ids = tuple(
                assignments_by_requirement.get(
                    requirement_id,
                    (),
                )
            )

            if assigned_teacher_ids:
                teacher_option_count = len(
                    set(assigned_teacher_ids)
                )
            else:
                teacher_option_count = 1

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
                    entity_value(
                        variable,
                        "teacher_id",
                        default=None,
                    )
                    for variable in actual_variables
                },
                key=lambda value: str(value),
            )

            actual_teacher_labels = []

            for teacher_id in actual_teacher_ids:
                if teacher_id is None:
                    actual_teacher_labels.append("NO_TEACHER")
                else:
                    actual_teacher_labels.append(
                        teacher_label(
                            domain_teachers.get(teacher_id)
                        )
                    )

            mismatch = actual_count != expected_count

            if mismatch:
                mismatches += 1

            print(
                f"{'MISMATCH' if mismatch else 'OK':8} | "
                f"GROUP={group_label(group):30} | "
                f"SUBJECT={subject_label(requirement):8} | "
                f"WEEK={entity_value(requirement, 'periods_per_week', default='?'):>2} | "
                f"ASSIGNED_TEACHERS={len(set(assigned_teacher_ids)):>2} | "
                f"ACTUAL_TEACHERS={','.join(actual_teacher_labels) or '<NONE>'} | "
                f"EXPECTED={expected_count:>5} | "
                f"ACTUAL={actual_count:>5}"
            )

        print()

        # ------------------------------------------------------------------
        # 9. MODEL DIMENSION
        # ------------------------------------------------------------------

        print("9. MODEL DIMENSION AFTER VARIABLE CREATION")
        print("-" * 110)

        proto = model.proto

        print(f"MODEL VARIABLES:   {len(proto.variables)}")
        print(f"MODEL CONSTRAINTS: {len(proto.constraints)}")
        print(f"MODEL OBJECTIVE:   {bool(proto.objective)}")
        print()

        # ------------------------------------------------------------------
        # 10. FINAL EVIDENCE
        # ------------------------------------------------------------------

        print("10. FINAL RECONCILIATION")
        print("-" * 110)
        print(f"EXPECTED VARIABLE TOTAL: {expected_total}")
        print(f"ACTUAL VARIABLE TOTAL:   {actual_total}")
        print(f"REQUIREMENT MISMATCHES:  {mismatches}")
        print()

        if actual_total == expected_total and mismatches == 0:
            print(
                "RESULT: PASS - production variable dimensions match "
                "the loaded teacher-assignment data."
            )
        else:
            print(
                "RESULT: FAIL - production variable dimensions do NOT "
                "match the loaded teacher-assignment data."
            )

        if actual_total == 7840:
            print()
            print(
                "DIMENSION FACT: 7,840 = 40 requirements × 49 slots × 4 rooms."
            )

        print()
        print("=" * 110)
        print("READ-ONLY: NO DATABASE CHANGES")
        print("=" * 110)
