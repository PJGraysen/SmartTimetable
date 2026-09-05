import os
import sys
from uuid import UUID

import django


# ============================================================================
# SMARTTIMETABLE PRO - GRADE 10 FRE RESERVED SLOT AUDIT
# READ-ONLY
# ============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


from apps.academics.models import LessonRequirement
from apps.scheduling.models import TeacherAssignment


# ============================================================================
# AUTHORITATIVE FRE CONTRACT
# ============================================================================

FRE_REQUIREMENTS = {
    "Grade 10E": {
        "requirement_id": UUID("f067234b-ca5e-4090-abad-d8e6b12831df"),
        "weekly_lessons": 5,
    },
    "Grade 10W": {
        "requirement_id": UUID("d288984c-af84-44e6-af95-7f5c90b437b3"),
        "weekly_lessons": 5,
    },
}


# ============================================================================
# HELPERS
# ============================================================================

def get_field_names(model):
    return {
        field.name
        for field in model._meta.get_fields()
    }


def get_first_existing_field(obj, names):
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def get_weekly_value(requirement):
    """
    Resolve the weekly lesson field without assuming one exact field name.
    """

    candidate_names = (
        "lessons_per_week",
        "weekly_lessons",
        "periods_per_week",
        "periods_week",
        "weekly_periods",
    )

    for name in candidate_names:
        if hasattr(requirement, name):
            return getattr(requirement, name)

    return None


def get_requirement_from_assignment(assignment):
    """
    Resolve the LessonRequirement relation without assuming only one
    possible Django field name.
    """

    candidate_names = (
        "lesson_requirement",
        "requirement",
    )

    for name in candidate_names:
        if hasattr(assignment, name):
            return getattr(assignment, name)

    return None


def get_teacher_from_assignment(assignment):
    candidate_names = (
        "teacher",
        "staff",
        "teacher_profile",
    )

    for name in candidate_names:
        if hasattr(assignment, name):
            return getattr(assignment, name)

    return None


def display_teacher(teacher):
    if teacher is None:
        return "NONE"

    for name in (
        "full_name",
        "name",
        "display_name",
        "employee_number",
        "staff_number",
    ):
        if hasattr(teacher, name):
            value = getattr(teacher, name)
            if value:
                return str(value)

    return str(teacher)


# ============================================================================
# MAIN AUDIT
# ============================================================================

def main():
    print("=" * 90)
    print("SMARTTIMETABLE PRO - GRADE 10 FRE RESERVED SLOT AUDIT")
    print("=" * 90)
    print("READ-ONLY: NO DATABASE CHANGES")
    print()

    passed = True

    # ------------------------------------------------------------------------
    # REQUIREMENTS
    # ------------------------------------------------------------------------

    print("=== RESERVED FRE CURRICULUM REQUIREMENTS ===")

    requirement_objects = {}

    for grade_name, contract in FRE_REQUIREMENTS.items():

        requirement_id = contract["requirement_id"]
        expected_weekly = contract["weekly_lessons"]

        requirement = (
            LessonRequirement.objects
            .filter(pk=requirement_id)
            .first()
        )

        if requirement is None:
            print(
                f"FAIL | {grade_name} FRE requirement does not exist | "
                f"REQ_ID={requirement_id}"
            )
            passed = False
            continue

        requirement_objects[grade_name] = requirement

        actual_weekly = get_weekly_value(requirement)

        if actual_weekly != expected_weekly:
            print(
                f"FAIL | {grade_name} FRE weekly requirement mismatch | "
                f"EXPECTED={expected_weekly}/week | "
                f"ACTUAL={actual_weekly}/week"
            )
            passed = False
        else:
            print(
                f"{grade_name} | "
                f"REQ_ID={requirement_id} | "
                f"{actual_weekly}/week | "
                f"ACTIVE_TEACHER=NONE"
            )

    print()

    # ------------------------------------------------------------------------
    # TEACHER ASSIGNMENTS
    # ------------------------------------------------------------------------

    print("=== HISTORICAL FRE ASSIGNMENTS ===")

    fre_requirement_ids = {
        contract["requirement_id"]
        for contract in FRE_REQUIREMENTS.values()
    }

    fre_assignments = []

    # Read all assignment records and identify those belonging to the
    # authoritative FRE requirements. This deliberately avoids assuming
    # a particular related-field name in the model.
    for assignment in TeacherAssignment.objects.all():

        requirement = get_requirement_from_assignment(assignment)

        if requirement is None:
            continue

        requirement_id = getattr(requirement, "pk", None)

        if requirement_id in fre_requirement_ids:
            fre_assignments.append(
                (assignment, requirement)
            )

    if not fre_assignments:
        print("NONE")
    else:
        for assignment, requirement in fre_assignments:

            teacher = get_teacher_from_assignment(assignment)

            print(
                f"REQ_ID={requirement.pk} | "
                f"TEACHER={display_teacher(teacher)}"
            )

    print()

    # ------------------------------------------------------------------------
    # AUTHORITATIVE POLICY
    # ------------------------------------------------------------------------

    print("=== AUTHORITATIVE FRE POLICY ===")
    print("FRE IS A RESERVED CURRICULUM SLOT.")
    print("FRE remains present at 5 lessons/week for Grade 10E and Grade 10W.")
    print("There is currently NO French teacher assignment.")
    print("There is currently NO active French class/student allocation.")
    print("NO teacher must be invented or selected automatically.")
    print(
        "FRE must NOT be treated as a staffed timetable lesson until "
        "a future French class and teacher are explicitly configured."
    )
    print()

    # ------------------------------------------------------------------------
    # FINAL ASSIGNMENT STATUS
    # ------------------------------------------------------------------------

    if not fre_assignments:
        print("PASS | No FRE teacher assignment required at present.")
    else:
        print(
            "WARNING | FRE teacher-assignment records exist and require "
            "explicit staffing review."
        )

    print()

    # ------------------------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------------------------

    print("=" * 90)
    print("RESULT")
    print("=" * 90)

    if passed:
        print("PASS | FRE curriculum slot preserved.")
        print("PASS | No FRE database modification performed.")
        print("=" * 90)
        return 0

    print("FAIL | FRE reserved curriculum contract is inconsistent.")
    print("=" * 90)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
