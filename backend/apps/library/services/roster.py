"""
Roster sync — turn platform Students and Teachers/Staff into Library Members.
"""
from __future__ import annotations

from django.db import transaction

from apps.library.models import Member


def _clean(s: str) -> str:
    return "".join(c for c in (s or "") if c.isalnum() or c in "-_")


@transaction.atomic
def sync_roster() -> dict:
    from apps.academics.models import Student
    from apps.users.models import Teacher

    created_students = 0
    created_teachers = 0
    updated = 0

    for s in Student.objects.filter(is_active=True):
        number = f"STU-{_clean(s.admission_number)}"
        existing = Member.objects.filter(student=s).first()
        if existing:
            changed = False
            if existing.full_name != s.full_name:
                existing.full_name = s.full_name; changed = True
            if not existing.is_active:
                existing.is_active = True; changed = True
            if changed:
                existing.save(); updated += 1
            continue
        # avoid clash if a Member already uses this member_number
        if Member.objects.filter(member_number=number).exists():
            number = f"STU-{_clean(s.admission_number)}-{str(s.id)[:6]}"
        Member.objects.create(
            student=s, member_number=number, full_name=s.full_name,
            member_type=Member.MemberType.STUDENT, is_active=True,
        )
        created_students += 1

    for t in Teacher.objects.filter(is_active=True):
        full = f"{t.first_name} {t.last_name}".strip() or t.employee_code
        number = f"TCH-{_clean(t.employee_code)}"
        existing = Member.objects.filter(teacher=t).first()
        if existing:
            changed = False
            if existing.full_name != full:
                existing.full_name = full; changed = True
            if existing.user_id != t.user_id:
                existing.user = t.user; changed = True
            if not existing.is_active:
                existing.is_active = True; changed = True
            if changed:
                existing.save(); updated += 1
            continue
        if Member.objects.filter(member_number=number).exists():
            number = f"TCH-{_clean(t.employee_code)}-{str(t.id)[:6]}"
        Member.objects.create(
            teacher=t, user=t.user, member_number=number, full_name=full,
            member_type=Member.MemberType.TEACHER, is_active=True,
        )
        created_teachers += 1

    return {
        "created_students": created_students,
        "created_teachers": created_teachers,
        "updated": updated,
        "total_members": Member.objects.count(),
    }


def eligible_people() -> dict:
    """Return students/teachers that do NOT yet have a library Member row."""
    from apps.academics.models import Student
    from apps.users.models import Teacher

    linked_student_ids = set(
        Member.objects.filter(student__isnull=False).values_list("student_id", flat=True)
    )
    linked_teacher_ids = set(
        Member.objects.filter(teacher__isnull=False).values_list("teacher_id", flat=True)
    )
    students = list(
        Student.objects.filter(is_active=True)
        .exclude(id__in=linked_student_ids)
        .values("id", "admission_number", "first_name", "last_name", "status")
    )
    teachers = list(
        Teacher.objects.filter(is_active=True)
        .exclude(id__in=linked_teacher_ids)
        .values("id", "employee_code", "first_name", "last_name", "role")
    )
    return {"students": students, "teachers": teachers}
