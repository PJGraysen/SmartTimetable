"""
Teacher admin extras: assignment grid, subject/class dropdowns,
teacher creation. Wired into /api/platform/admin/teachers/.

Kept separate from TeacherAdminViewSet so we don't disturb the
existing freeze/unfreeze/deactivate actions.
"""
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.users.models import Teacher, User
from apps.academics.models import Subject, InstructionalGroup, LessonRequirement
from apps.core.models import Term
from apps.inventory.models import Department


def _load_for_teacher(t):
    """Return every active+inactive LessonRequirement for a teacher."""
    return (
        LessonRequirement.objects
        .filter(teacher=t)
        .select_related("subject", "instructional_group", "term")
        .order_by("instructional_group__name", "subject__code")
    )


def _lr_payload(lr):
    return {
        "id": str(lr.id),
        "subject_id": lr.subject_id,
        "subject_code": lr.subject.code if lr.subject else None,
        "subject_name": lr.subject.name if lr.subject else None,
        "class_id": str(lr.instructional_group_id),
        "class_name": lr.instructional_group.name if lr.instructional_group else None,
        "lessons_per_week": lr.lessons_per_week,
        "requirement_type": getattr(lr, "requirement_type", None),
        "is_active": lr.is_active,
    }


@api_view(["GET"])
@permission_classes([IsAdminUser])
def teacher_assignments(request, pk):
    try:
        t = Teacher.objects.get(id=pk)
    except Teacher.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    lrs = list(_load_for_teacher(t))
    total = sum(l.lessons_per_week for l in lrs if l.is_active)
    return Response({
        "teacher_id": str(t.id),
        "full_name": str(t),
        "employee_code": t.employee_code,
        "teacher_number": t.teacher_number,
        "total_lessons": total,
        "capacity": 46,
        "assignments": [_lr_payload(l) for l in lrs],
    })


@api_view(["POST"])
@permission_classes([IsAdminUser])
def teacher_assign(request, pk):
    """Create or update a LessonRequirement for this teacher."""
    try:
        t = Teacher.objects.get(id=pk)
    except Teacher.DoesNotExist:
        return Response({"detail": "teacher not found"}, status=404)

    subject_id = request.data.get("subject_id")
    class_id = request.data.get("class_id")
    lessons = int(request.data.get("lessons_per_week") or 0)
    req_type = request.data.get("requirement_type") or "STANDALONE"

    if not subject_id or not class_id or lessons <= 0:
        return Response({"detail": "subject_id, class_id, lessons_per_week required"}, status=400)

    try:
        subj = Subject.objects.get(id=subject_id)
        ig = InstructionalGroup.objects.get(id=class_id)
    except (Subject.DoesNotExist, InstructionalGroup.DoesNotExist):
        return Response({"detail": "subject or class not found"}, status=404)

    term = Term.objects.filter(is_active=True).first() or Term.objects.first()
    if not term:
        return Response({"detail": "no term"}, status=400)

    with transaction.atomic():
        lr, created = LessonRequirement.objects.get_or_create(
            teacher=t, subject=subj, instructional_group=ig, term=term,
            defaults={
                "lessons_per_week": lessons,
                "requirement_type": req_type,
                "is_active": True,
            },
        )
        if not created:
            lr.lessons_per_week = lessons
            lr.requirement_type = req_type
            lr.is_active = True
            lr.save(update_fields=["lessons_per_week", "requirement_type", "is_active", "updated_at"])
    return Response({"ok": True, "created": created, "assignment": _lr_payload(lr)})


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def teacher_unassign(request, pk, lr_id):
    try:
        t = Teacher.objects.get(id=pk)
    except Teacher.DoesNotExist:
        return Response({"detail": "teacher not found"}, status=404)
    qs = LessonRequirement.objects.filter(id=lr_id, teacher=t)
    if not qs.exists():
        return Response({"detail": "assignment not found for this teacher"}, status=404)
    qs.delete()
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def teacher_create(request):
    """Create a new teacher with role, department, phone, hire_date."""
    from django.db import IntegrityError

    data = request.data
    code = (data.get("employee_code") or "").strip()
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()

    if not code:
        return Response({"detail": "Employee Code is required (e.g. T021)"}, status=400)
    if not first:
        return Response({"detail": "First Name is required"}, status=400)
    if Teacher.objects.filter(employee_code=code).exists():
        return Response({"detail": f"Employee code {code} already exists"}, status=409)

    role = (data.get("role") or "TEACHER").strip().upper()
    valid_roles = {r for r, _ in Teacher.ROLE_CHOICES}
    if role not in valid_roles:
        return Response({"detail": f"Invalid role '{role}'. Valid: {sorted(valid_roles)}"}, status=400)

    email = (data.get("email") or "").strip() or None
    if email and "@" not in email:
        return Response({"detail": "Email must be a valid address (e.g. name@school.ac.ke)"}, status=400)

    teacher_number = data.get("teacher_number")
    if teacher_number in ("", None, "null"):
        teacher_number = None
    else:
        try:
            teacher_number = int(teacher_number)
        except (TypeError, ValueError):
            return Response({"detail": "Teacher # must be a number (e.g. 21)"}, status=400)
        if teacher_number <= 0:
            return Response({"detail": "Teacher # must be positive"}, status=400)
        existing = Teacher.objects.filter(teacher_number=teacher_number).first()
        if existing:
            return Response({
                "detail": (
                    f"Teacher # {teacher_number} is already used by "
                    f"{existing.employee_code} ({existing}). "
                    "Leave blank or pick a different number."
                ),
            }, status=409)

    username = (data.get("username") or code).strip().lower()
    password = data.get("password") or None

    dept_id = data.get("department_id") or None
    hire_date = data.get("hire_date") or None
    phone = (data.get("phone") or "").strip()

    try:
        with transaction.atomic():
            user, _created = User.objects.get_or_create(
                username=username,
                defaults={"email": email or "", "is_active": True},
            )
            if password:
                user.set_password(password)
            if email:
                user.email = email
            user.save()

            t = Teacher.objects.create(
                user=user,
                employee_code=code,
                teacher_number=teacher_number,
                first_name=first,
                last_name=last,
                role=role,
                phone=phone,
                hire_date=hire_date,
                department_id=dept_id,
                is_active=True,
                is_frozen=False,
            )
    except IntegrityError as exc:
        msg = str(exc)
        if "employee_code" in msg:
            return Response({"detail": f"Employee code {code} already exists"}, status=409)
        if "teacher_number" in msg:
            return Response({"detail": "Teacher # already in use"}, status=409)
        return Response({"detail": f"Could not create teacher: {msg}"}, status=400)

    return Response({"ok": True, "id": str(t.id)})




@api_view(["GET"])
@permission_classes([IsAdminUser])
def subjects_list(request):
    rows = Subject.objects.filter(is_active=True).order_by("code")
    return Response({"results": [
        {"id": s.id, "code": s.code, "name": s.name} for s in rows
    ]})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def classes_list(request):
    rows = InstructionalGroup.objects.all().order_by("name")
    return Response({"results": [
        {"id": str(g.id), "name": g.name, "is_active": g.is_active} for g in rows
    ]})



@api_view(["PATCH"])
@permission_classes([IsAdminUser])
def teacher_update_profile(request, pk):
    """Update extended teacher fields (department, role, phone, names, email)."""
    try:
        t = Teacher.objects.select_related("user").get(id=pk)
    except Teacher.DoesNotExist:
        return Response({"detail": "teacher not found"}, status=404)

    data = request.data
    upd = []

    for field in ("first_name", "last_name", "phone"):
        if field in data:
            setattr(t, field, str(data[field] or "").strip())
            upd.append(field)

    if "employee_code" in data:
        code = str(data["employee_code"] or "").strip()
        if code and code != t.employee_code:
            if Teacher.objects.filter(employee_code=code).exclude(id=t.id).exists():
                return Response({"detail": f"employee_code {code} already in use"}, status=409)
            t.employee_code = code
            upd.append("employee_code")

    if "teacher_number" in data:
        num = data["teacher_number"]
        if num in ("", None):
            t.teacher_number = None
        else:
            try:
                num = int(num)
            except (TypeError, ValueError):
                return Response({"detail": "teacher_number must be an integer"}, status=400)
            if num <= 0:
                return Response({"detail": "teacher_number must be positive"}, status=400)
            if Teacher.objects.filter(teacher_number=num).exclude(id=t.id).exists():
                return Response({"detail": f"teacher_number {num} already in use"}, status=409)
            t.teacher_number = num
        upd.append("teacher_number")

    if "role" in data:
        role = str(data["role"] or "").strip().upper()
        valid = {r for r, _ in Teacher.ROLE_CHOICES}
        if role not in valid:
            return Response({"detail": f"invalid role. valid: {sorted(valid)}"}, status=400)
        t.role = role
        upd.append("role")

    if "department_id" in data:
        dept_id = data["department_id"]
        if dept_id in ("", None):
            t.department = None
        else:
            try:
                t.department = Department.objects.get(id=dept_id)
            except Department.DoesNotExist:
                return Response({"detail": "department not found"}, status=404)
        upd.append("department")

    if "hire_date" in data:
        t.hire_date = data["hire_date"] or None
        upd.append("hire_date")

    if "email" in data and t.user_id:
        t.user.email = str(data["email"] or "").strip()
        t.user.save(update_fields=["email"])

    if upd:
        t.save(update_fields=upd + ["updated_at"])
    return Response({"ok": True, "updated": upd})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def teacher_bulk_assign(request, pk):
    """
    Assign the same subject to multiple classes for one teacher.
    Body: { subject_id, class_ids: [uuid, ...], lessons_per_week, requirement_type? }
    Returns per-class created/updated/skipped.
    """
    try:
        t = Teacher.objects.get(id=pk)
    except Teacher.DoesNotExist:
        return Response({"detail": "teacher not found"}, status=404)

    subject_id = request.data.get("subject_id")
    class_ids = request.data.get("class_ids") or []
    lessons = int(request.data.get("lessons_per_week") or 0)
    req_type = request.data.get("requirement_type") or "STANDALONE"

    if not subject_id or not class_ids or lessons <= 0:
        return Response({"detail": "subject_id, class_ids, lessons_per_week required"}, status=400)

    try:
        subj = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response({"detail": "subject not found"}, status=404)

    term = Term.objects.filter(is_active=True).first() or Term.objects.first()
    if not term:
        return Response({"detail": "no term"}, status=400)

    results = []
    total_new_load = 0
    with transaction.atomic():
        for cid in class_ids:
            try:
                ig = InstructionalGroup.objects.get(id=cid)
            except InstructionalGroup.DoesNotExist:
                results.append({"class_id": cid, "status": "class_not_found"})
                continue
            lr, created = LessonRequirement.objects.get_or_create(
                teacher=t, subject=subj, instructional_group=ig, term=term,
                defaults={
                    "lessons_per_week": lessons,
                    "requirement_type": req_type,
                    "is_active": True,
                },
            )
            if created:
                results.append({"class_id": cid, "class_name": ig.name, "status": "created"})
                total_new_load += lessons
            else:
                old = lr.lessons_per_week
                if old != lessons or not lr.is_active:
                    lr.lessons_per_week = lessons
                    lr.is_active = True
                    lr.save(update_fields=["lessons_per_week", "is_active", "updated_at"])
                    results.append({"class_id": cid, "class_name": ig.name,
                                    "status": "updated", "from": old, "to": lessons})
                    total_new_load += (lessons - old)
                else:
                    results.append({"class_id": cid, "class_name": ig.name,
                                    "status": "unchanged"})

    # Capacity check (informational, does not reject)
    current_load = sum(l.lessons_per_week for l in LessonRequirement.objects.filter(teacher=t, is_active=True))
    return Response({
        "ok": True,
        "results": results,
        "teacher_new_load": current_load,
        "capacity": 46,
        "over_capacity": current_load > 46,
    })


@api_view(["DELETE", "POST"])
@permission_classes([IsAdminUser])
def teacher_delete(request, pk):
    """Safe delete. Refuses if any timetable history references this teacher
    (either directly via teacher FK, or indirectly via any of their lesson
    requirements). Returns 409 with a suggestion to deactivate."""
    from django.db.models import Q

    try:
        t = Teacher.objects.get(id=pk)
    except Teacher.DoesNotExist:
        return Response({"detail": "teacher not found"}, status=404)

    # Count history: direct teacher ref OR any timetable entry that uses
    # any of this teacher's lesson requirements.
    te_count = 0
    try:
        from apps.scheduling.models import TimetableEntry
        te_count = TimetableEntry.objects.filter(
            Q(teacher=t) | Q(lesson_requirement__teacher=t)
        ).distinct().count()
    except Exception:
        te_count = 0

    if te_count > 0:
        return Response({
            "detail": (
                f"Cannot delete: this teacher is referenced by "
                f"{te_count} timetable entries (historical records). "
                "Deactivate instead — history preserved, removed from future runs."
            ),
            "te_count": te_count,
            "suggestion": "deactivate",
        }, status=409)

    # Count assignments
    lr_count = t.lesson_requirements.count() if hasattr(t, "lesson_requirements") else 0

    with transaction.atomic():
        if lr_count:
            t.lesson_requirements.all().delete()
        t.delete()

    return Response({"ok": True, "deleted_assignments": lr_count}, status=200)
