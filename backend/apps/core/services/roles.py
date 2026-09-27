"""Resolve the primary role for a user across the platform."""
from __future__ import annotations


ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_LIBRARIAN = "LIBRARIAN"
ROLE_DEPT_HEAD = "DEPT_HEAD"
ROLE_TEACHER = "TEACHER"
ROLE_STAFF = "STAFF"
ROLE_STUDENT = "STUDENT"
ROLE_GUEST = "GUEST"


_LANDING = {
    ROLE_SUPER_ADMIN: "/",
    ROLE_LIBRARIAN: "/library",
    ROLE_DEPT_HEAD: "/",
    ROLE_TEACHER: "/library/my",
    ROLE_STAFF: "/library/my",
    ROLE_STUDENT: "/library/my",
    ROLE_GUEST: "/library/public",
}


def user_primary_role(user) -> str:
    if not user or not getattr(user, "is_authenticated", False):
        return ROLE_GUEST
    if getattr(user, "is_superuser", False):
        return ROLE_SUPER_ADMIN

    # Django group membership — highest priority wins
    groups = set(user.groups.values_list("name", flat=True))
    if "Librarian" in groups:
        return ROLE_LIBRARIAN

    # Teacher profile role
    teacher = getattr(user, "teacher_profile", None)
    if teacher is not None:
        r = (getattr(teacher, "role", "") or "").upper()
        if r == "LIBRARIAN":
            return ROLE_LIBRARIAN
        if r == "DEPT_HEAD":
            return ROLE_DEPT_HEAD
        if r in ("TEACHER", "LAB_TECH", "AUDITOR", "PROCUREMENT", "BURSAR", "OTHER"):
            return ROLE_TEACHER

    # Student profile
    if getattr(user, "student_profile", None) is not None:
        return ROLE_STUDENT

    # Library Member fallback
    m = getattr(user, "library_member", None)
    if m is not None:
        t = (m.member_type or "").upper()
        if t == "STUDENT":
            return ROLE_STUDENT
        if t == "LIBRARIAN":
            return ROLE_LIBRARIAN
        if t in ("TEACHER", "STAFF"):
            return ROLE_TEACHER

    if getattr(user, "is_staff", False):
        return ROLE_STAFF
    return ROLE_GUEST


def landing_path(role: str) -> str:
    return _LANDING.get(role, "/")
