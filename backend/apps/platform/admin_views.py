"""Platform admin console endpoints (superuser/staff only)."""
import shutil
from django.contrib.auth.models import User, Group
from django.db.models import Count
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and (u.is_superuser or u.is_staff))


def _user_payload(u):
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "is_active": u.is_active,
        "is_staff": u.is_staff,
        "is_superuser": u.is_superuser,
        "groups": list(u.groups.values_list("name", flat=True)),
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "date_joined": u.date_joined.isoformat() if u.date_joined else None,
    }


class AdminUsersView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = User.objects.all().order_by("username").prefetch_related("groups")
        q = request.query_params.get("q")
        if q:
            qs = qs.filter(username__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q)
        users = [_user_payload(u) for u in qs[:500]]
        return Response({"count": len(users), "results": users})

    def post(self, request):
        data = request.data
        username = (data.get("username") or "").strip()
        password = data.get("password") or "ChangeMe123!"
        if not username:
            return Response({"detail": "username required"}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({"detail": "username already exists"}, status=400)
        u = User.objects.create_user(
            username=username,
            email=(data.get("email") or "").strip(),
            password=password,
            first_name=(data.get("first_name") or "").strip(),
            last_name=(data.get("last_name") or "").strip(),
            is_staff=bool(data.get("is_staff", False)),
            is_superuser=bool(data.get("is_superuser", False)),
            is_active=bool(data.get("is_active", True)),
        )
        for gname in (data.get("groups") or []):
            g, _ = Group.objects.get_or_create(name=gname)
            u.groups.add(g)
        return Response(_user_payload(u), status=201)


class AdminUserDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, user_id):
        try:
            u = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "not found"}, status=404)
        return Response(_user_payload(u))

    def patch(self, request, user_id):
        try:
            u = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "not found"}, status=404)
        d = request.data
        for f in ["email", "first_name", "last_name"]:
            if f in d:
                setattr(u, f, d[f])
        for f in ["is_active", "is_staff", "is_superuser"]:
            if f in d:
                setattr(u, f, bool(d[f]))
        u.save()
        if "groups" in d and isinstance(d["groups"], list):
            u.groups.clear()
            for gname in d["groups"]:
                g, _ = Group.objects.get_or_create(name=gname)
                u.groups.add(g)
        return Response(_user_payload(u))

    def delete(self, request, user_id):
        if int(user_id) == int(request.user.id):
            return Response({"detail": "cannot delete yourself"}, status=400)
        try:
            u = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "not found"}, status=404)
        u.delete()
        return Response({"deleted": True})


class AdminUserResetPasswordView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        try:
            u = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "not found"}, status=404)
        new_pass = request.data.get("password") or "ChangeMe123!"
        u.set_password(new_pass)
        u.save()
        return Response({"ok": True, "username": u.username})


class AdminGroupsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        rows = []
        for g in Group.objects.all().order_by("name"):
            rows.append({
                "id": g.id,
                "name": g.name,
                "user_count": g.user_set.count(),
                "permission_count": g.permissions.count(),
            })
        return Response(rows)

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "name required"}, status=400)
        g, created = Group.objects.get_or_create(name=name)
        return Response({"id": g.id, "name": g.name, "created": created}, status=201 if created else 200)


class AdminGroupDetailView(APIView):
    permission_classes = [IsAdmin]

    def delete(self, request, group_id):
        try:
            g = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({"detail": "not found"}, status=404)
        if g.name in ("Teacher", "Administrator", "Viewer"):
            return Response({"detail": "system group cannot be deleted"}, status=400)
        g.delete()
        return Response({"deleted": True})


class AdminHealthView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from apps.academics.models import (
            Student, Result, Assessment, TeachingGroup, LessonRequirement,
            RankingRule, AcademicAuditEvent,
        )
        try:
            db_ok = True
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception:
            db_ok = False

        total, used, free = shutil.disk_usage(".")
        disk = {
            "total_gb": round(total / (1024**3), 2),
            "used_gb":  round(used / (1024**3), 2),
            "free_gb":  round(free / (1024**3), 2),
            "used_pct": round(used / total * 100, 1),
        }
        counts = {
            "students":          Student.objects.count(),
            "results":           Result.objects.count(),
            "assessments":       Assessment.objects.count(),
            "teaching_groups":   TeachingGroup.objects.count(),
            "lesson_requirements": LessonRequirement.objects.count(),
            "ranking_rules":     RankingRule.objects.count(),
            "audit_events":      AcademicAuditEvent.objects.count(),
            "users":             User.objects.count(),
            "groups":            Group.objects.count(),
        }
        recent_audit = list(
            AcademicAuditEvent.objects.order_by("-created_at")[:10]
            .values("created_at", "action", "entity_type", "entity_label")
        )
        return Response({
            "db_ok": db_ok,
            "disk": disk,
            "counts": counts,
            "recent_audit": recent_audit,
            "server_time": __import__("datetime").datetime.utcnow().isoformat(),
        })


class AdminWarningsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from apps.academics.models import (
            Student, Result, TeachingGroup, LessonRequirement,
            Assessment, ResultStatus,
        )
        warnings = []

        # Students without enrolment
        no_enrol = Student.objects.filter(is_active=True, enrollments__isnull=True).count()
        if no_enrol:
            warnings.append({
                "severity": "warning",
                "title": f"{no_enrol} active student(s) without class enrolment",
                "detail": "These students will not appear in class-level views.",
            })

        # Lesson requirements without teacher
        lr_no_teacher = LessonRequirement.objects.filter(is_active=True, teacher__isnull=True).count()
        if lr_no_teacher:
            warnings.append({
                "severity": "warning",
                "title": f"{lr_no_teacher} lesson requirement(s) without assigned teacher",
                "detail": "Marks entry is unconstrained for these classes/subjects.",
            })

        # Published assessments with no results
        for a in Assessment.objects.filter(status="PUBLISHED"):
            n = Result.objects.filter(assessment=a).count()
            if n == 0:
                warnings.append({
                    "severity": "info",
                    "title": f"Assessment '{a.name}' has no marks yet",
                    "detail": f"Status PUBLISHED, {a.date}.",
                })

        # Classes with no active students
        for tg in TeachingGroup.objects.filter(is_active=True):
            n = tg.enrollments.filter(is_current=True).count()
            if n == 0:
                warnings.append({
                    "severity": "warning",
                    "title": f"Class '{tg.name}' has no active students",
                    "detail": "Either not seeded or the stream is empty.",
                })

        # Very low pass rate hint (per assessment)
        for a in Assessment.objects.all()[:5]:
            rs = Result.objects.filter(assessment=a, status=ResultStatus.VALID)
            if rs.count() > 0:
                below = sum(1 for r in rs if float(r.raw_mark or 0) < 40)
                if below > rs.count() * 0.5:
                    warnings.append({
                        "severity": "danger",
                        "title": f"Over half of '{a.name}' below 40%",
                        "detail": f"{below} of {rs.count()} results.",
                    })

        return Response({"count": len(warnings), "warnings": warnings})


# ---------------------------------------------------------------------
# Teacher admin (added 2026-09-20)
# ---------------------------------------------------------------------
from rest_framework.viewsets import ViewSet as _VS2
from rest_framework.decorators import action as _action2
from apps.users.models import Teacher as _Teacher
from apps.academics.models import LessonRequirement as _LR


def _teacher_payload(t):
    lrs = _LR.objects.filter(teacher=t, is_active=True).select_related(
        "subject", "instructional_group__teaching_group"
    )
    assignments = sorted({
        f"{lr.subject.code} / {lr.instructional_group.teaching_group.name}"
        for lr in lrs
    })
    return {
        "id": str(t.id),
        "employee_code": t.employee_code,
        "teacher_number": t.teacher_number,
        "first_name": t.first_name,
        "last_name": t.last_name,
        "full_name": f"{t.first_name} {t.last_name}".strip(),
        "username": t.user.username if t.user else None,
        "email": t.user.email if t.user else None,
        "is_active": t.is_active,
        "is_frozen": getattr(t, "is_frozen", False),
        "lr_count": lrs.count(),
        "assignments": assignments,
    }


class TeacherAdminViewSet(_VS2):
    """
    /api/platform/admin/teachers/                    list / create
    /api/platform/admin/teachers/<id>/               detail / patch / delete
    /api/platform/admin/teachers/<id>/freeze/        POST
    /api/platform/admin/teachers/<id>/unfreeze/      POST
    /api/platform/admin/teachers/<id>/activate/      POST
    /api/platform/admin/teachers/<id>/deactivate/    POST
    """

    def list(self, request):
        qs = _Teacher.objects.select_related("user").order_by("employee_code")
        q = request.query_params.get("q")
        if q:
            qs = qs.filter(employee_code__icontains=q) | qs.filter(last_name__icontains=q) | qs.filter(first_name__icontains=q)
        return Response({
            "count": qs.count(),
            "results": [_teacher_payload(t) for t in qs[:500]],
        })

    def retrieve(self, request, pk=None):
        try:
            t = _Teacher.objects.select_related("user").get(id=pk)
        except _Teacher.DoesNotExist:
            return Response({"detail": "not found"}, status=404)
        return Response(_teacher_payload(t))

    def partial_update(self, request, pk=None):
        try:
            t = _Teacher.objects.select_related("user").get(id=pk)
        except _Teacher.DoesNotExist:
            return Response({"detail": "not found"}, status=404)
        for f in ("first_name", "last_name"):
            if f in request.data:
                setattr(t, f, request.data[f])
        if "teacher_number" in request.data:
            v = request.data["teacher_number"]
            t.teacher_number = int(v) if v not in (None, "") else None
        t.save()
        return Response(_teacher_payload(t))

    def destroy(self, request, pk=None):
        try:
            t = _Teacher.objects.select_related("user").get(id=pk)
        except _Teacher.DoesNotExist:
            return Response({"detail": "not found"}, status=404)
        n_lr = _LR.objects.filter(teacher=t).count()
        if n_lr > 0:
            return Response({
                "detail": f"Teacher has {n_lr} lesson requirement(s). "
                          f"Deactivate or reassign first, or use freeze.",
            }, status=400)
        from apps.scheduling.models import TimetableEntry as _TE
        n_te = _TE.objects.filter(teacher=t).count()
        if n_te > 0:
            return Response({
                "detail": f"Teacher appears in {n_te} timetable entr(ies). "
                          f"Delete is not permitted; use freeze.",
            }, status=400)
        t.delete()
        return Response({"deleted": True})

    @_action2(detail=True, methods=["post"], url_path="freeze")
    def freeze(self, request, pk=None):
        t = _Teacher.objects.get(id=pk)
        t.is_frozen = True
        t.save(update_fields=["is_frozen", "updated_at"])
        return Response(_teacher_payload(t))

    @_action2(detail=True, methods=["post"], url_path="unfreeze")
    def unfreeze(self, request, pk=None):
        t = _Teacher.objects.get(id=pk)
        t.is_frozen = False
        t.save(update_fields=["is_frozen", "updated_at"])
        return Response(_teacher_payload(t))

    @_action2(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        t = _Teacher.objects.get(id=pk)
        t.is_active = True
        t.save(update_fields=["is_active", "updated_at"])
        return Response(_teacher_payload(t))

    @_action2(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        t = _Teacher.objects.get(id=pk)
        t.is_active = False
        t.save(update_fields=["is_active", "updated_at"])
        return Response(_teacher_payload(t))
