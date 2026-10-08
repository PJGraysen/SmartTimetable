"""
Teacher-scoped permissions. Used by the academics viewsets to enforce
"a teacher only sees their subjects/classes/students".
"""
from rest_framework.permissions import BasePermission

from apps.academics.teacher_scope import (
    is_admin_like, teacher_can_access_class, teacher_can_access_student,
    teacher_can_access_subject, can_edit_grading,
)


class IsAdminLike(BasePermission):
    """Super admin / principal / admin / secretary only."""
    message = "This action requires an academic administrator."
    def has_permission(self, request, view):
        return is_admin_like(request.user)


class CanEditGrading(BasePermission):
    """Only admin-like roles can modify grading schemes."""
    message = "Only academic administrators can modify grading schemes."
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return can_edit_grading(request.user)
