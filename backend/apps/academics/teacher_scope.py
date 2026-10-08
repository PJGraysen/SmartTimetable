"""
Teacher-scope helpers. Every "teacher sees only their subjects" rule routes
through these functions so we have one place to reason about ownership.

A teacher "handles":
  - a class (InstructionalGroup) if they have any active LessonRequirement
    for that class
  - a subject if they have any active LessonRequirement for that subject
  - a student if the student is enrolled in a class the teacher handles
"""
from django.db.models import QuerySet

from apps.academics.models import LessonRequirement, InstructionalGroup, Student
from apps.core.roles import Role, primary_role


def is_admin_like(user) -> bool:
    """Super admin, principal, admin, secretary see everything."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return primary_role(user) in (
        Role.SUPER_ADMIN, Role.PRINCIPAL, Role.ADMIN, Role.SECRETARY,
    )


def is_dept_head(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return primary_role(user) == Role.DEPT_HEAD


def teacher_record(user):
    """Return the Teacher row for a user, or None.

    The reverse accessor on User is named `teacher_profile` on this
    codebase, but older code sometimes uses `teacher`. Try both, then
    fall back to a direct query so this never silently returns None.
    """
    if not user or not user.is_authenticated:
        return None

    for attr in ("teacher_profile", "teacher"):
        try:
            v = getattr(user, attr, None)
            if v is not None:
                return v
        except Exception:
            pass

    from apps.users.models import Teacher
    return Teacher.objects.filter(user=user).first()


def teacher_lesson_requirements(user):
    """Active LessonRequirements owned by this user's Teacher record."""
    t = teacher_record(user)
    if not t:
        return LessonRequirement.objects.none()
    return LessonRequirement.objects.filter(teacher=t, is_active=True)


def teacher_classes(user) -> QuerySet:
    """Distinct InstructionalGroups this teacher handles."""
    if is_admin_like(user):
        return InstructionalGroup.objects.filter(is_active=True)
    lrs = teacher_lesson_requirements(user)
    ig_ids = lrs.values_list("instructional_group_id", flat=True).distinct()
    return InstructionalGroup.objects.filter(id__in=list(ig_ids), is_active=True)


def teacher_subject_ids(user):
    """Set of subject IDs this teacher handles."""
    if is_admin_like(user):
        return None  # None = "all subjects"
    lrs = teacher_lesson_requirements(user)
    return set(lrs.values_list("subject_id", flat=True).distinct())


def teacher_student_ids(user):
    """Set of student IDs in classes this teacher handles.

    An InstructionalGroup's parent is a TeachingGroup; students are enrolled
    on the TeachingGroup (StudentEnrollment.teaching_group). So we go:
        IG -> teaching_group_id -> StudentEnrollment.teaching_group
    """
    if is_admin_like(user):
        return None  # None = "all students"
    ig_ids = list(teacher_classes(user).values_list("id", flat=True))
    if not ig_ids:
        return set()
    # Map InstructionalGroup ids -> their parent TeachingGroup ids
    tg_ids = list(
        InstructionalGroup.objects.filter(id__in=ig_ids)
        .values_list("teaching_group_id", flat=True)
        .distinct()
    )
    if not tg_ids:
        return set()
    return set(
        Student.objects.filter(
            enrollments__teaching_group_id__in=tg_ids,
            enrollments__is_current=True,
        ).values_list("id", flat=True).distinct()
    )


def teacher_can_access_class(user, ig_id) -> bool:
    if is_admin_like(user):
        return True
    return teacher_classes(user).filter(id=ig_id).exists()


def teacher_can_access_subject(user, subject_id) -> bool:
    if is_admin_like(user):
        return True
    return subject_id in (teacher_subject_ids(user) or set())


def teacher_can_access_student(user, student_id) -> bool:
    if is_admin_like(user):
        return True
    return student_id in (teacher_student_ids(user) or set())


def can_edit_grading(user) -> bool:
    """Only admin-like roles can edit grading schemes."""
    return is_admin_like(user)
