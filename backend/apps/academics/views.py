from django.shortcuts import render

# Create your views here.



from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.academics.models import Student
from apps.academics.serializers import (
    StudentSerializer,
    StudentEnrollmentSerializer,
)


from rest_framework.permissions import IsAuthenticated
from apps.academics.teacher_scope import (
    is_admin_like, teacher_student_ids, teacher_can_access_subject,
)
from apps.academics.permissions import IsAdminLike, CanEditGrading


class StudentViewSet(viewsets.ModelViewSet):
    """
    Read/write academic student records.

    GET    /api/academics/students/
    POST   /api/academics/students/
    GET    /api/academics/students/{id}/
    PATCH  /api/academics/students/{id}/
    DELETE /api/academics/students/{id}/
    GET    /api/academics/students/by-group/?teaching_group=<uuid>
    GET    /api/academics/students/{id}/enrollments/
    """

    queryset = Student.objects.all().order_by("last_name", "first_name")
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        ids = teacher_student_ids(self.request.user)
        if ids is None:
            return qs
        return qs.filter(id__in=ids)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "admission_number", "first_name", "middle_name", "last_name",
    ]
    ordering_fields = [
        "admission_number", "last_name", "first_name", "created_at",
    ]

    @action(detail=True, methods=["get"], url_path="enrollments")
    def enrollments(self, request, pk=None):
        student = self.get_object()
        qs = student.enrollments.select_related(
            "teaching_group", "academic_year",
        )
        return Response(StudentEnrollmentSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="by-group")
    def by_group(self, request):
        group_id = request.query_params.get("teaching_group")
        if not group_id:
            return Response(
                {"detail": "teaching_group query param required"},
                status=400,
            )
        qs = Student.objects.filter(
            enrollments__teaching_group_id=group_id,
            enrollments__is_current=True,
        ).distinct()
        ids = teacher_student_ids(request.user)
        if ids is not None:
            qs = qs.filter(id__in=ids)
        return Response(StudentSerializer(qs, many=True).data)



# ---------------------------------------------------------------------
# Academic analysis API (added 2026-09-16)
# ---------------------------------------------------------------------
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status as _status

from apps.academics import analysis as _analysis
from apps.academics.models import Assessment as _Assessment


class _AnalysisBase(APIView):
    permission_classes = [IsAuthenticated]


class AnalysisAssessmentsView(_AnalysisBase):
    def get(self, request):
        return Response(_analysis.list_assessments())


class AnalysisDashboardView(_AnalysisBase):
    def get(self, request):
        from apps.academics.teacher_scope import (
            teacher_classes, teacher_subject_ids, teacher_student_ids,
            is_admin_like,
        )
        scope_whole = (request.query_params.get("scope") or "").lower() == "whole"
        scope_classes = None if (is_admin_like(request.user) or scope_whole) else set(teacher_classes(request.user).values_list("id", flat=True))
        scope_subjects = None if (is_admin_like(request.user) or scope_whole) else teacher_subject_ids(request.user)
        scope_students = None if (is_admin_like(request.user) or scope_whole) else teacher_student_ids(request.user)
        aid = request.query_params.get("assessment")
        if not aid:
            latest = _Assessment.objects.order_by("-date").first()
            if not latest:
                return Response({"detail": "No assessments"}, status=404)
            aid = latest.id
        try:
            data = _analysis.dashboard(aid)
        except _Assessment.DoesNotExist:
            return Response({"detail": "Assessment not found"}, status=404)
        # Attach trend across all assessments for chart
        all_ids = list(_Assessment.objects.order_by("date").values_list("id", flat=True))
        data["trend"] = _analysis.trend(all_ids)
        # ---- teacher scoping: trim per-subject rows to subjects they handle ----
        if scope_subjects is not None and isinstance(data, dict):
            allowed = {str(s) for s in scope_subjects}
            for key in ("subjects", "subject_rows", "per_subject"):
                if isinstance(data.get(key), list):
                    data[key] = [
                        r for r in data[key]
                        if str(r.get("subject_id")) in allowed
                    ]
        return Response(data)


class AnalysisStudentView(_AnalysisBase):
    def get(self, request, student_id):
        from apps.academics.models import Student, Result, ResultStatus
        try:
            s = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"detail": "Student not found"}, status=404)
        _ids = teacher_student_ids(request.user)
        if _ids is not None and s.id not in _ids:
            return Response({"detail": "You cannot view this student."}, status=403)
        scheme = _analysis._active_scheme()
        results = (
            Result.objects.filter(student=s)
            .select_related("assessment", "subject")
            .order_by("assessment__date", "subject__name")
        )
        by_subject = {}
        for r in results:
            if r.status != ResultStatus.VALID:
                continue
            pct = _analysis._pct(r.raw_mark, r.assessment.max_mark)
            if pct is None:
                continue
            by_subject.setdefault(r.subject.code, {
                "subject_code": r.subject.code,
                "subject_name": r.subject.name,
                "marks": [],
            })["marks"].append({
                "assessment": r.assessment.name,
                "date": r.assessment.date.isoformat(),
                "pct": pct,
                "grade": (_analysis.grade_for(scheme, pct) or {}).get("grade", "-"),
            })
        for row in by_subject.values():
            pcts = [m["pct"] for m in row["marks"]]
            row["mean"] = round(sum(pcts) / len(pcts), 2) if pcts else 0
            row["trend"] = "stable"
            if len(pcts) >= 2:
                delta = pcts[-1] - pcts[0]
                row["trend"] = "improving" if delta > 3 else "declining" if delta < -3 else "stable"
        return Response({
            "student": {
                "id": str(s.id),
                "admission_number": s.admission_number,
                "name": s.full_name,
                "status": s.status,
            },
            "subjects": sorted(by_subject.values(), key=lambda x: -x["mean"]),
        })



class AnalysisStudentDeepView(_AnalysisBase):
    def get(self, request, student_id):
        from apps.academics.models import Student
        try:
            _s = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"detail": "Student not found"}, status=404)
        _ids = teacher_student_ids(request.user)
        if _ids is not None and _s.id not in _ids:
            return Response({"detail": "You cannot view this student."}, status=403)
        data = _analysis.student_deep_analysis(student_id)
        return Response(data)



# ---------------------------------------------------------------------
# Assessment + Marks entry API (added 2026-09-17)
# ---------------------------------------------------------------------
from apps.academics.serializers import (
    AssessmentSerializer as _AssessmentSer,
    ResultBulkWriteSerializer as _RBulkSer,
)
from apps.academics.models import (
    Assessment as _Assessment,
    Result as _Result,
    ResultStatus as _ResultStatus,
    Student as _Student,
    Subject as _Subject,
)


class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = _Assessment.objects.all().order_by("-date")
    serializer_class = _AssessmentSer
    permission_classes = [IsAdminLike]

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        a = self.get_object()
        a.status = "PUBLISHED"
        a.save(update_fields=["status", "updated_at"])
        _log_audit_event(request, "PUBLISH", "Assessment", a.name, entity_id=a.id)
        return Response(_AssessmentSer(a).data)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        a = self.get_object()
        a.status = "ARCHIVED"
        a.save(update_fields=["status", "updated_at"])
        _log_audit_event(request, "ARCHIVE", "Assessment", a.name, entity_id=a.id)
        return Response(_AssessmentSer(a).data)

    @action(detail=True, methods=["post"], url_path="draft")
    def draft(self, request, pk=None):
        a = self.get_object()
        a.status = "DRAFT"
        a.save(update_fields=["status", "updated_at"])
        _log_audit_event(request, "UNPUBLISH", "Assessment", a.name, entity_id=a.id)
        return Response(_AssessmentSer(a).data)

    @action(detail=True, methods=["post"], url_path="open-marks")
    def open_marks(self, request, pk=None):
        a = self.get_object()
        a.status = "MARK_ENTRY"
        a.save(update_fields=["status", "updated_at"])
        _log_audit_event(
            request, "STATUS_CHANGE", "Assessment", a.name,
            entity_id=a.id, meta={"to": "MARK_ENTRY"},
        )
        return Response(_AssessmentSer(a).data)


class ResultViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="roster")
    def roster(self, request):
        aid = request.query_params.get("assessment")
        sid = request.query_params.get("subject")
        if not (aid and sid):
            return Response({"detail": "assessment and subject required"}, status=400)
        try:
            a = _Assessment.objects.get(id=aid)
            subj = _Subject.objects.get(id=sid)
        except (_Assessment.DoesNotExist, _Subject.DoesNotExist):
            return Response({"detail": "not found"}, status=404)

        _u = request.user
        _is_admin = bool(
            _u and getattr(_u, "is_authenticated", False)
            and (_u.is_staff or _u.is_superuser)
        )
        if not _is_admin and a.status != "MARK_ENTRY":
            return Response(
                {"detail": f"Marks entry is closed for this assessment (status: {a.status})."},
                status=403,
            )

        if not is_admin_like(request.user):
            if not teacher_can_access_subject(request.user, subj.id):
                return Response({"detail": "You do not teach this subject."}, status=403)

        students = _Student.objects.filter(is_active=True).order_by("last_name", "first_name")
        _tids = teacher_student_ids(request.user)
        if _tids is not None:
            students = students.filter(id__in=_tids)
        existing = {
            r.student_id: r
            for r in _Result.objects.filter(assessment=a, subject=subj)
        }
        rows = []
        for s in students:
            r = existing.get(s.id)
            rows.append({
                "student_id": str(s.id),
                "admission_number": s.admission_number,
                "name": s.full_name,
                "raw_mark": float(r.raw_mark) if (r and r.raw_mark is not None) else None,
                "status": r.status if r else "MISSING",
            })
        return Response(rows)

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        ser = _RBulkSer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            a = _Assessment.objects.get(id=ser.validated_data["assessment"])
            subj = _Subject.objects.get(id=ser.validated_data["subject"])
        except (_Assessment.DoesNotExist, _Subject.DoesNotExist):
            return Response({"detail": "not found"}, status=404)        # Bulk marks gating (teacher-scoped + publication-aware)
        _u = request.user
        _is_admin = is_admin_like(_u)

        if not _is_admin:
            if not teacher_can_access_subject(_u, subj.id):
                return Response({"detail": "You do not teach this subject."}, status=403)
            if a.status != "MARK_ENTRY":
                return Response(
                    {"detail": f"Marks entry is closed for this assessment (status:{a.status})."},
                    status=403,
                )
            try:
                from apps.academics.models import ResultPublication
                from apps.core.models import Term
                _active = Term.objects.filter(is_active=True).first()
                _pub = ResultPublication.objects.filter(term=_active).first() if _active else None
                if _pub and _pub.is_published:
                    return Response(
                        {"detail": "Results have been published. Marks entry is locked."},
                        status=403,
                    )
            except Exception:
                pass

        created = 0
        updated = 0
        skipped = 0
        _allowed_ids = teacher_student_ids(_u)
        _allowed_set = {str(x) for x in _allowed_ids} if _allowed_ids is not None else None
        for row in ser.validated_data["marks"]:
            student_id = row.get("student") or row.get("student_id")
            raw = row.get("raw_mark")
            stat = row.get("status", "VALID")
            if (raw is None or raw == "") and stat == "VALID":
                stat = "MISSING"
            if not student_id:
                continue
            if _allowed_set is not None and str(student_id) not in _allowed_set:
                skipped += 1
                continue
            obj, was_created = _Result.objects.update_or_create(
                assessment=a,
                subject=subj,
                student_id=student_id,
                defaults={"raw_mark": raw if raw not in ("", None) else None, "status": stat},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        _log_audit_event(
            request,
            action="BULK_UPDATE",
            entity_type="Result",
            entity_label=f"{created + updated} marks — {subj.code} on {a.name}",
            entity_id=a.id,
            meta={"created": created, "updated": updated,
                  "subject": subj.code, "assessment": a.name},
        )
        return Response({"created": created, "updated": updated})



class AnalysisClassComparisonView(_AnalysisBase):
    def get(self, request):
        from apps.academics.teacher_scope import (
            teacher_classes, teacher_subject_ids, teacher_student_ids,
            is_admin_like,
        )
        scope_whole = (request.query_params.get("scope") or "").lower() == "whole"
        scope_classes = None if (is_admin_like(request.user) or scope_whole) else set(teacher_classes(request.user).values_list("id", flat=True))
        scope_subjects = None if (is_admin_like(request.user) or scope_whole) else teacher_subject_ids(request.user)
        scope_students = None if (is_admin_like(request.user) or scope_whole) else teacher_student_ids(request.user)
        aid = request.query_params.get("assessment")
        if not aid:
            latest = _Assessment.objects.order_by("-date").first()
            if not latest:
                return Response({"detail": "No assessments"}, status=404)
            aid = latest.id
        try:
            data = _analysis.class_comparison_v2(aid)
        except _Assessment.DoesNotExist:
            return Response({"detail": "Assessment not found"}, status=404)
        # ---- teacher scoping ----
        # scope_classes holds InstructionalGroup.ids; class comparison rows
        # use TeachingGroup.ids. Translate before comparing.
        if scope_classes is not None and isinstance(data, dict):
            from apps.academics.models import InstructionalGroup as _IG2
            allowed_tg = set(
                str(tg_id)
                for tg_id in _IG2.objects.filter(id__in=list(scope_classes))
                .values_list("teaching_group_id", flat=True)
            )
            for key in ("classes", "class_rows", "rows"):
                if isinstance(data.get(key), list):
                    data[key] = [
                        r for r in data[key]
                        if str(r.get("group_id")) in allowed_tg
                    ]
            if isinstance(data.get("subject_gaps"), list):
                allowed = {str(s) for s in (scope_subjects or set())}
                data["subject_gaps"] = [
                    g for g in data["subject_gaps"]
                    if str(g.get("subject_id")) in allowed
                ]
        return Response(data)





# ---------------------------------------------------------------------
# /analysis/me/ — the logged-in student's own performance
# ---------------------------------------------------------------------


def _get_student_for_user(user):
    """Return the Student row linked to this user, or None.

    Tries the known related_name ("student_profile") first, then falls
    back to a direct query so this survives FK renames.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return None
    # Fast path via the FK's related_name
    try:
        s = getattr(user, "student_profile", None)
        if s is not None:
            return s
    except Exception:
        pass
    # Direct query fallback
    from apps.academics.models import Student
    return Student.objects.filter(user=user).first()

class AnalysisMyPerformanceView(_AnalysisBase):
    """
    Student's own performance - exhaustive analytics vs. class and history.
    """
    def get(self, request):
        import statistics as _stats
        from apps.academics.models import (
            Student, StudentEnrollment, Result, ResultStatus,
            InstructionalGroup,
        )
        from apps.academics import analysis as A

        u = request.user
        student = _get_student_for_user(u)
        if student is None:
            return Response(
                {"detail": "No student profile linked to your account."},
                status=404,
            )

        scheme = A._active_scheme()

        enrollments = list(StudentEnrollment.objects.filter(
            student=student, is_current=True,
        ).select_related("teaching_group"))
        class_ids = [e.teaching_group_id for e in enrollments if e.teaching_group_id]
        class_label = ""
        if enrollments:
            tg = getattr(enrollments[0], "teaching_group", None)
            class_label = getattr(tg, "name", None) or ""

        # Peers = students in the same teaching group(s)
        peer_ids = []
        if class_ids:
            peer_ids = list(Student.objects.filter(
                enrollments__teaching_group_id__in=class_ids,
                enrollments__is_current=True,
            ).distinct().values_list("id", flat=True))

        my_results = list(Result.objects.filter(
            student=student, status=ResultStatus.VALID,
        ).select_related("assessment", "subject"))

        peer_results = list(Result.objects.filter(
            student_id__in=peer_ids, status=ResultStatus.VALID,
        ).select_related("assessment", "subject")) if peer_ids else []

        subj_scores_all = {}
        subj_scores_mine = {}
        for r in peer_results:
            pct = A._pct(r.raw_mark, r.assessment.max_mark)
            if pct is None:
                continue
            subj_scores_all.setdefault(str(r.subject_id), []).append(pct)
        for r in my_results:
            pct = A._pct(r.raw_mark, r.assessment.max_mark)
            if pct is None:
                continue
            grade = (A.grade_for(scheme, pct) or {}).get("grade", "-")
            subj_scores_mine.setdefault(str(r.subject_id), []).append({
                "assessment_id": str(r.assessment_id),
                "name": r.assessment.name,
                "date": r.assessment.date.isoformat() if r.assessment.date else "",
                "pct": round(pct, 2),
                "grade": grade,
                "subject_code": r.subject.code,
                "subject_name": r.subject.name,
            })

        subject_rows = []
        for sid, exams in subj_scores_mine.items():
            exams.sort(key=lambda x: x["date"])
            pcts = [e["pct"] for e in exams]
            mean = round(sum(pcts) / len(pcts), 2) if pcts else 0
            grade = (A.grade_for(scheme, mean) or {}).get("grade", "-")

            trend = "stable"
            if len(pcts) >= 2:
                delta = pcts[-1] - pcts[0]
                trend = ("improving" if delta > 3
                         else "declining" if delta < -3
                         else "stable")

            consistency_sd = round(_stats.pstdev(pcts), 2) if len(pcts) >= 2 else 0.0
            consistency = (
                "very consistent" if consistency_sd < 4
                else "consistent" if consistency_sd < 8
                else "variable" if consistency_sd < 15
                else "volatile"
            )

            class_pcts = subj_scores_all.get(sid, [])
            class_mean = round(sum(class_pcts) / len(class_pcts), 2) if class_pcts else None
            class_median = round(_stats.median(class_pcts), 2) if class_pcts else None
            delta_class = round(mean - class_mean, 2) if class_mean is not None else None

            percentile = None
            if class_pcts:
                below = sum(1 for v in class_pcts if v < mean)
                percentile = round(100 * below / len(class_pcts))

            best = max(exams, key=lambda x: x["pct"]) if exams else None
            worst = min(exams, key=lambda x: x["pct"]) if exams else None

            subject_rows.append({
                "subject_id": sid,
                "code": exams[0]["subject_code"],
                "name": exams[0]["subject_name"],
                "mean": mean,
                "grade": grade,
                "trend": trend,
                "consistency": consistency,
                "consistency_sd": consistency_sd,
                "class_mean": class_mean,
                "class_median": class_median,
                "delta_class": delta_class,
                "percentile": percentile,
                "exam_count": len(exams),
                "best": best,
                "worst": worst,
                "exams": exams[-6:],
            })

        subject_rows.sort(key=lambda x: -x["mean"])

        all_my_pcts = []
        for s in subject_rows:
            for e in s["exams"]:
                all_my_pcts.append(e["pct"])
        overall = round(sum(all_my_pcts) / len(all_my_pcts), 2) if all_my_pcts else 0

        all_class_pcts = []
        for lst in subj_scores_all.values():
            all_class_pcts.extend(lst)
        class_overall = round(sum(all_class_pcts) / len(all_class_pcts), 2) if all_class_pcts else None
        overall_delta = round(overall - class_overall, 2) if class_overall is not None else None

        class_rank = None
        class_size = None
        if peer_ids:
            peer_means = {}
            for pid in peer_ids:
                rs = [r for r in peer_results if r.student_id == pid]
                pcts2 = [A._pct(r.raw_mark, r.assessment.max_mark) for r in rs]
                pcts2 = [p for p in pcts2 if p is not None]
                if pcts2:
                    peer_means[pid] = sum(pcts2) / len(pcts2)
            ordered = sorted(peer_means.items(), key=lambda x: -x[1])
            class_size = len(ordered)
            for i, (pid, _) in enumerate(ordered, start=1):
                if pid == student.id:
                    class_rank = i
                    break

        overall_percentile = None
        if class_rank and class_size:
            overall_percentile = round(100 * (class_size - class_rank) / class_size)

        overall_sd = round(_stats.pstdev(all_my_pcts), 2) if len(all_my_pcts) >= 2 else 0.0

        strengths = sorted(
            [s for s in subject_rows if s["delta_class"] is None or s["delta_class"] >= 0],
            key=lambda s: -(s["delta_class"] or 0),
        )[:3]
        focus = sorted(
            [s for s in subject_rows if s["delta_class"] is None or s["delta_class"] < 0],
            key=lambda s: (s["delta_class"] or 0),
        )[:3]
        if not focus:
            focus = sorted(subject_rows, key=lambda s: s["mean"])[:3]

        exam_map = {}
        for s in subject_rows:
            for e in s["exams"]:
                key = e["assessment_id"]
                node = exam_map.setdefault(key, {
                    "name": e["name"],
                    "date": e["date"],
                    "pcts": [],
                })
                node["pcts"].append(e["pct"])
        recent_exams = []
        for node in sorted(exam_map.values(), key=lambda x: x["date"], reverse=True)[:4]:
            my_mean = round(sum(node["pcts"]) / len(node["pcts"]), 2) if node["pcts"] else 0
            recent_exams.append({
                "name": node["name"],
                "date": node["date"],
                "mean": my_mean,
                "subject_count": len(node["pcts"]),
            })

        return Response({
            "student": {
                "id": str(student.id),
                "name": student.full_name,
                "admission": student.admission_number,
                "klass": class_label,
            },
            "overall": {
                "mean": overall,
                "class_mean": class_overall,
                "delta": overall_delta,
                "class_rank": class_rank,
                "class_size": class_size,
                "percentile": overall_percentile,
                "std_dev": overall_sd,
                "subject_count": len(subject_rows),
                "exam_count": len(recent_exams),
            },
            "subjects": subject_rows,
            "strengths": strengths,
            "focus": focus,
            "recent_exams": recent_exams,
        })





# ---------------------------------------------------------------------
# /analysis/teacher/me/ — teacher's own subjects & classes analytics
# ---------------------------------------------------------------------
class AnalysisTeacherPerformanceView(_AnalysisBase):
    """
    Rich analytics for a teacher: their subjects, classes, students,
    and comparisons.

    Shows EVERY subject, class, and student the teacher is assigned to,
    even where no results exist yet (stats default to zero / dash).
    """

    def get(self, request):
        import statistics as _stats
        from apps.academics.models import (
            Student, StudentEnrollment, Result, ResultStatus,
            InstructionalGroup, Subject, LessonRequirement, Assessment,
        )
        from apps.users.models import Teacher
        from apps.academics import analysis as A

        u = request.user

        # ---- Resolve teacher ----
        teacher = None
        for attr in ("teacher_profile", "teacher"):
            try:
                v = getattr(u, attr, None)
                if v is not None:
                    teacher = v
                    break
            except Exception:
                pass
        if teacher is None:
            teacher = Teacher.objects.filter(user=u).first()
        if teacher is None:
            return Response({"detail": "No teacher profile linked to your account."}, status=404)

        scheme = A._active_scheme()

        # ---- Teacher's LRs (direct FK + scheduling TeacherAssignment union) ----
        direct_lr_ids = set(
            LessonRequirement.objects.filter(teacher=teacher, is_active=True)
            .values_list("id", flat=True)
        )
        assignment_lr_ids = set()
        try:
            from apps.scheduling.models import TeacherAssignment
            assignment_lr_ids = set(
                TeacherAssignment.objects.filter(teacher=teacher, is_active=True)
                .values_list("lesson_requirement_id", flat=True)
            )
        except Exception:
            pass
        combined_lr_ids = direct_lr_ids | assignment_lr_ids

        lrs = list(
            LessonRequirement.objects.filter(id__in=combined_lr_ids, is_active=True)
            .select_related("subject", "instructional_group")
        )
        subject_ids = list({lr.subject_id for lr in lrs if lr.subject_id})
        group_ids = list({lr.instructional_group_id for lr in lrs if lr.instructional_group_id})

        my_subjects = list(Subject.objects.filter(id__in=subject_ids))
        subject_map = {s.id: s for s in my_subjects}

        my_groups = list(InstructionalGroup.objects.filter(id__in=group_ids))
        group_map = {g.id: g for g in my_groups}

        teaching_group_ids = list(
            InstructionalGroup.objects.filter(id__in=group_ids)
            .values_list("teaching_group_id", flat=True).distinct()
        )

        # ---- ALL students in my teaching groups (with or without results) ----
        student_ids = list(
            StudentEnrollment.objects.filter(
                teaching_group_id__in=teaching_group_ids, is_current=True,
            ).values_list("student_id", flat=True).distinct()
        )
        students = {str(s.id): s for s in Student.objects.filter(id__in=student_ids)}

        # student -> set of teaching-group ids
        student_groups = {}
        for sid, tid in StudentEnrollment.objects.filter(
            student_id__in=student_ids, is_current=True,
        ).values_list("student_id", "teaching_group_id"):
            student_groups.setdefault(str(sid), set()).add(tid)

        # ---- Results ----
        my_results = list(
            Result.objects.filter(
                student_id__in=student_ids,
                subject_id__in=subject_ids,
                status=ResultStatus.VALID,
            ).select_related("assessment", "subject", "student")
        )

        # Class-wide results: all subjects taught in the teacher's classes
        # (used only for the class drill-down so "whole class" mode is complete).
        all_class_subject_ids = set()
        for _ig in my_groups:
            all_class_subject_ids.update(
                LessonRequirement.objects.filter(
                    instructional_group=_ig, is_active=True
                ).values_list("subject_id", flat=True)
            )
        class_wide_results = list(
            Result.objects.filter(
                student_id__in=student_ids,
                subject_id__in=all_class_subject_ids,
                status=ResultStatus.VALID,
            ).select_related("assessment", "subject", "student")
        )
        school_results = list(
            Result.objects.filter(
                subject_id__in=subject_ids,
                status=ResultStatus.VALID,
            ).select_related("assessment", "subject")
        )

        # ---- Buckets ----
        school_by_subject = {}
        for r in school_results:
            pct = A._pct(r.raw_mark, r.assessment.max_mark)
            if pct is None:
                continue
            school_by_subject.setdefault(str(r.subject_id), []).append(pct)

        my_by_subject = {}
        my_by_student = {}
        my_by_class = {}
        for r in my_results:
            pct = A._pct(r.raw_mark, r.assessment.max_mark)
            if pct is None:
                continue
            grade = (A.grade_for(scheme, pct) or {}).get("grade", "\u2014")
            aid = str(r.assessment_id)
            sid = str(r.subject_id)
            stid = str(r.student_id)
            entry = {
                "student_id": stid,
                "assessment_id": aid,
                "name": r.assessment.name,
                "date": r.assessment.date.isoformat() if r.assessment.date else "",
                "pct": round(pct, 2),
                "grade": grade,
                "subject_code": r.subject.code,
                "subject_name": r.subject.name,
            }
            my_by_subject.setdefault(sid, []).append(entry)
            my_by_student.setdefault(stid, []).append(entry)

        # Class-wide bucket: every subject, every student in the class
        my_by_class_wide = {}
        for r in class_wide_results:
            pct = A._pct(r.raw_mark, r.assessment.max_mark)
            if pct is None:
                continue
            grade = (A.grade_for(scheme, pct) or {}).get("grade", "\u2014")
            entry = {
                "student_id": str(r.student_id),
                "assessment_id": str(r.assessment_id),
                "name": r.assessment.name,
                "date": r.assessment.date.isoformat() if r.assessment.date else "",
                "pct": round(pct, 2),
                "grade": grade,
                "subject_code": r.subject.code,
                "subject_name": r.subject.name,
            }
            for tid in student_groups.get(str(r.student_id), ()):
                for g in my_groups:
                    if g.teaching_group_id == tid:
                        my_by_class_wide.setdefault(str(g.id), []).append(entry)

        # ---- Overall KPI ----
        all_my_pcts = [e["pct"] for s in my_by_subject.values() for e in s]
        overall = round(sum(all_my_pcts) / len(all_my_pcts), 2) if all_my_pcts else 0

        all_school_pcts = [p for lst in school_by_subject.values() for p in lst]
        school_overall = round(sum(all_school_pcts) / len(all_school_pcts), 2) if all_school_pcts else None
        overall_delta = round(overall - school_overall, 2) if school_overall is not None else None
        overall_sd = round(_stats.pstdev(all_my_pcts), 2) if len(all_my_pcts) >= 2 else 0.0

        # ============================================================
        # Subjects — every assigned subject, results or not
        # ============================================================
        subject_rows = []
        for sid in subject_ids:
            sid_str = str(sid)
            exams = list(my_by_subject.get(sid_str, []))
            exams.sort(key=lambda x: x["date"])
            pcts = [e["pct"] for e in exams]

            subj = subject_map.get(sid)
            subj_code = subj.code if subj else (exams[0]["subject_code"] if exams else "?")
            subj_name = subj.name if subj else (exams[0]["subject_name"] if exams else "?")

            if pcts:
                mean = round(sum(pcts) / len(pcts), 2)
                grade = (A.grade_for(scheme, mean) or {}).get("grade", "\u2014")
                trend = "stable"
                if len(pcts) >= 2:
                    d = pcts[-1] - pcts[0]
                    trend = "improving" if d > 3 else "declining" if d < -3 else "stable"
                sd = round(_stats.pstdev(pcts), 2) if len(pcts) >= 2 else 0.0
                consistency = (
                    "very consistent" if sd < 4
                    else "consistent" if sd < 8
                    else "variable" if sd < 15
                    else "volatile"
                )
            else:
                mean, grade, trend, sd, consistency = 0, "\u2014", "stable", 0.0, "no data"

            school_pcts = school_by_subject.get(sid_str, [])
            school_mean = round(sum(school_pcts) / len(school_pcts), 2) if school_pcts else None
            delta = round(mean - school_mean, 2) if (school_mean is not None and pcts) else None

            student_count = len({e["student_id"] for e in exams})

            # dedupe series by (name, date)
            series_map = {}
            for e in exams:
                k = (e["name"], e["date"])
                node = series_map.setdefault(k, {"name": e["name"], "date": e["date"], "pcts": []})
                node["pcts"].append(e["pct"])
            series_list = sorted(
                [{"name": v["name"], "date": v["date"],
                  "mean": round(sum(v["pcts"]) / len(v["pcts"]), 2)}
                 for v in series_map.values()],
                key=lambda x: x["date"],
            )

            dist = {}
            for e in exams:
                dist[e["grade"]] = dist.get(e["grade"], 0) + 1

            # Build per-assessment exam list (one row per distinct exam)
            # so the frontend Trends chart gets 12 distinct points, not
            # the last 6 individual student results.
            exams_by_assessment = {}
            for e in exams:
                key = e["assessment_id"]
                node = exams_by_assessment.setdefault(key, {
                    "assessment_id": key,
                    "name": e["name"],
                    "date": e["date"],
                    "subject_code": e["subject_code"],
                    "subject_name": e["subject_name"],
                    "pcts": [],
                    "grades": {},
                })
                node["pcts"].append(e["pct"])
                node["grades"][e["grade"]] = node["grades"].get(e["grade"], 0) + 1

            exams_flat = []
            for node in exams_by_assessment.values():
                avg = round(sum(node["pcts"]) / len(node["pcts"]), 2) if node["pcts"] else 0
                exams_flat.append({
                    "assessment_id": node["assessment_id"],
                    "name": node["name"],
                    "date": node["date"],
                    "pct": avg,
                    "grade": (A.grade_for(scheme, avg) or {}).get("grade", "\u2014"),
                    "subject_code": node["subject_code"],
                    "subject_name": node["subject_name"],
                    "student_count": len(node["pcts"]),
                })
            exams_flat.sort(key=lambda x: x["date"])

            # Deviation: last exam mean minus mean of prior exams
            _dev = None
            if len(series_list) >= 2:
                _last = series_list[-1]["mean"]
                _prior = [x["mean"] for x in series_list[:-1]]
                _dev = round(_last - sum(_prior) / len(_prior), 2)

            subject_rows.append({
                "subject_id": sid_str,
                "code": subj_code,
                "name": subj_name,
                "mean": mean,
                "deviation": _dev,
                "grade": grade,
                "trend": trend,
                "consistency": consistency,
                "consistency_sd": sd,
                "school_mean": school_mean,
                "delta": delta,
                "exam_count": len(series_list),
                "student_count": student_count,
                "distribution": dist,
                "series": series_list,
                "exams": exams_flat[-12:],
            })
        subject_rows.sort(key=lambda x: (-x["mean"], x["code"]))

        # ============================================================
        # Classes — every assigned group, results or not
        # ============================================================
        class_rows = []
        for g in my_groups:
            gid = str(g.id)
            entries = list(my_by_class_wide.get(gid, []))

            means_by_student = {}
            for e in entries:
                means_by_student.setdefault(e["student_id"], []).append(e["pct"])
            class_means = {sid: _stats.mean(v) for sid, v in means_by_student.items()}
            class_avg = round(_stats.mean(class_means.values()), 2) if class_means else 0

            ordered = sorted(class_means.items(), key=lambda x: -x[1])
            top_ids = [sid for sid, _ in ordered[:3]]
            focus_ids = [sid for sid, _ in ordered[-3:]] if len(ordered) >= 3 else [sid for sid, _ in ordered]
            lookup = {sid: students.get(sid) for sid in class_means}

            class_series_map = {}
            for e in entries:
                k = (e["name"], e["date"])
                node = class_series_map.setdefault(k, {"name": e["name"], "date": e["date"], "pcts": []})
                node["pcts"].append(e["pct"])
            series_list = sorted(
                [{"name": v["name"], "date": v["date"],
                  "mean": round(sum(v["pcts"]) / len(v["pcts"]), 2)}
                 for v in class_series_map.values()],
                key=lambda x: x["date"],
            )

            dist = {}
            for e in entries:
                dist[e["grade"]] = dist.get(e["grade"], 0) + 1

            enrolled_count = sum(
                1 for sid, tids in student_groups.items() if g.teaching_group_id in tids
            ) or len(class_means)

            # ---- Build ClassRow-shaped drilldown (matches ClassComparison) ----
            # All subjects in the class, in_scope marks teacher's own subjects
            class_means_by_subject = {}
            class_grades_by_subject = {}
            for e in entries:
                sc = e["subject_code"]
                class_means_by_subject.setdefault(sc, []).append(e["pct"])
                class_grades_by_subject.setdefault(sc, {})
                class_grades_by_subject[sc][e["grade"]] = class_grades_by_subject[sc].get(e["grade"], 0) + 1

            # Include subjects with no results in the class (from LRs on this class's IG)
            ig_for_class = next((ig for ig in my_groups if str(ig.id) == gid), None)
            if ig_for_class is not None:
                class_lr_subject_ids = set(
                    LessonRequirement.objects.filter(
                        instructional_group=ig_for_class, is_active=True
                    ).values_list("subject_id", flat=True)
                )
            else:
                class_lr_subject_ids = set()

            all_subject_objs = {
                s.id: s for s in Subject.objects.filter(id__in=class_lr_subject_ids)
            }
            in_scope_subject_ids = set(subject_ids) & class_lr_subject_ids

            subject_full = []
            for sid2 in class_lr_subject_ids:
                subj2 = all_subject_objs.get(sid2)
                if subj2 is None:
                    continue
                scode = subj2.code
                spcts = class_means_by_subject.get(scode, [])
                if spcts:
                    smean = round(sum(spcts) / len(spcts), 2)
                    ssd = round(_stats.pstdev(spcts), 2) if len(spcts) >= 2 else 0.0
                    shi = round(max(spcts), 2)
                    slo = round(min(spcts), 2)
                else:
                    smean, ssd, shi, slo = 0.0, 0.0, 0.0, 0.0
                subject_full.append({
                    "code": scode,
                    "name": subj2.name,
                    "mean": smean,
                    "std_dev": ssd,
                    "highest": shi,
                    "lowest": slo,
                    "in_scope": sid2 in in_scope_subject_ids,
                })
            subject_full.sort(key=lambda x: (-x["mean"], x["code"]))

            # Class stats
            all_class_pcts = [e["pct"] for e in entries]
            if all_class_pcts:
                overall_mean = round(sum(all_class_pcts) / len(all_class_pcts), 2)
                srt = sorted(all_class_pcts)
                n = len(srt)
                overall_median = round(
                    srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2, 2
                )
                overall_sd = round(_stats.pstdev(all_class_pcts), 2) if n >= 2 else 0.0
                pass_rate = round(
                    100.0 * sum(1 for p in all_class_pcts if p >= 50) / n, 2
                )
            else:
                overall_mean, overall_median, overall_sd, pass_rate = 0.0, 0.0, 0.0, 0.0

            # Best/worst student of the class
            best_student = None
            worst_student = None
            if class_means:
                ordered2 = sorted(class_means.items(), key=lambda x: -x[1])
                top_sid, top_mean = ordered2[0]
                bot_sid, bot_mean = ordered2[-1]
                top_s = students.get(top_sid)
                bot_s = students.get(bot_sid)
                if top_s:
                    best_student = {
                        "id": top_sid,
                        "name": top_s.full_name,
                        "admission_number": getattr(top_s, "admission_number", ""),
                        "mean": round(top_mean, 2),
                    }
                if bot_s:
                    worst_student = {
                        "id": bot_sid,
                        "name": bot_s.full_name,
                        "admission_number": getattr(bot_s, "admission_number", ""),
                        "mean": round(bot_mean, 2),
                    }

            # Leading / trailing subject
            scoped_full = [s for s in subject_full if s["in_scope"] and s["mean"] > 0]
            leading_subject = None
            trailing_subject = None
            if scoped_full:
                lead = max(scoped_full, key=lambda x: x["mean"])
                trail = min(scoped_full, key=lambda x: x["mean"])
                leading_subject = {"code": lead["code"], "name": lead["name"], "mean": lead["mean"]}
                trailing_subject = {"code": trail["code"], "name": trail["name"], "mean": trail["mean"]}

            class_rows.append({
                "group_id": gid,
                "group_name": g.name,
                "student_count": enrolled_count,
                "mean": class_avg,
                "subject_count": len({e["subject_code"] for e in entries}),
                "distribution": dist,
                "series": series_list,
                "top": [
                    {"id": sid, "name": lookup[sid].full_name if lookup.get(sid) else "?",
                     "mean": round(class_means[sid], 2)}
                    for sid in top_ids if lookup.get(sid)
                ],
                "focus": [
                    {"id": sid, "name": lookup[sid].full_name if lookup.get(sid) else "?",
                     "mean": round(class_means[sid], 2)}
                    for sid in focus_ids if lookup.get(sid)
                ],
                # ---- ClassRow-compatible drilldown (same shape as ClassComparison) ----
                "students": enrolled_count,
                "overall_mean": overall_mean,
                "overall_median": overall_median,
                "overall_std_dev": overall_sd,
                "overall_pass_rate": pass_rate,
                "best_student": best_student,
                "worst_student": worst_student,
                "subject_means": {s["code"]: s["mean"] for s in subject_full},
                "subject_full": subject_full,
                "leading_subject": leading_subject,
                "trailing_subject": trailing_subject,
                "deviation": (
                    None if len(series_list) < 2
                    else round(
                        series_list[-1]["mean"]
                        - sum(x["mean"] for x in series_list[:-1]) / (len(series_list) - 1),
                        2,
                    )
                ),
                "stream_name": (
                    g.teaching_group.stream.name
                    if g.teaching_group and g.teaching_group.stream else None
                ),
                "stream_code": (
                    g.teaching_group.stream.code
                    if g.teaching_group and g.teaching_group.stream else None
                ),
            })
        class_rows.sort(key=lambda x: x["group_name"])

        # Assign rank across this teacher's classes (by overall_mean, descending)
        ranked = sorted(class_rows, key=lambda x: -x["overall_mean"])
        for i, row in enumerate(ranked, 1):
            row["rank"] = i

        # ============================================================
        # Students — every enrolled student, results or not
        # ============================================================
        student_rows = []
        for sid_str, s in students.items():
            entries = list(my_by_student.get(sid_str, []))
            pcts = [e["pct"] for e in entries]
            mean = round(sum(pcts) / len(pcts), 2) if pcts else 0
            best = max(entries, key=lambda x: x["pct"]) if entries else None
            worst = min(entries, key=lambda x: x["pct"]) if entries else None
            sd = round(_stats.pstdev(pcts), 2) if len(pcts) >= 2 else 0.0
            # Deviation from student's own prior exams
            _sdev = None
            _srt = sorted(entries, key=lambda x: x["date"])
            if len(_srt) >= 2:
                _last = _srt[-1]["pct"]
                _prior = [x["pct"] for x in _srt[:-1]]
                _sdev = round(_last - sum(_prior) / len(_prior), 2)

            student_rows.append({
                "id": sid_str,
                "name": s.full_name,
                "admission": getattr(s, "admission_number", ""),
                "mean": mean,
                "deviation": _sdev,
                "exam_count": len(entries),
                "best": best,
                "worst": worst,
                "sd": sd,
            })
        student_rows.sort(key=lambda x: -x["mean"])

        # ---- Distribution ----
        overall_dist = {}
        for entries in my_by_student.values():
            for e in entries:
                overall_dist[e["grade"]] = overall_dist.get(e["grade"], 0) + 1

        # ---- Coverage ----
        total_assessments = (
            Assessment.objects
            .filter(results__subject_id__in=subject_ids)
            .distinct()
            .count()
        )
        filled_assessments = len({e["assessment_id"] for s in my_by_subject.values() for e in s})
        coverage_pct = round(100 * filled_assessments / total_assessments, 1) if total_assessments else 0

        # ---- Strengths / focus (only subjects with results) ----
        strengths = sorted(
            [s for s in subject_rows if s["exam_count"] > 0 and (s["delta"] is None or s["delta"] >= 0)],
            key=lambda s: -(s["delta"] or 0),
        )[:3]
        focus_subj = sorted(
            [s for s in subject_rows if s["exam_count"] > 0 and s["delta"] is not None and s["delta"] < 0],
            key=lambda s: (s["delta"] or 0),
        )[:3]
        if not focus_subj:
            focus_subj = sorted([s for s in subject_rows if s["exam_count"] > 0], key=lambda s: s["mean"])[:3]

        # ---- Recent exams — collapse by (name, date) across subjects ----
        # Each subject now contributes one row per assessment via exams_flat,
        # so this map groups 4 subjects × 12 assessments into 12 distinct exams.
        exam_map = {}
        for s in subject_rows:
            for e in s["exams"]:
                k = (e["name"], e["date"])
                node = exam_map.setdefault(k, {
                    "name": e["name"],
                    "date": e["date"],
                    "pcts": [],
                    "subject_count": 0,
                })
                node["pcts"].append(e["pct"])
                node["subject_count"] += 1
        recent = []
        for node in sorted(exam_map.values(), key=lambda x: x["date"], reverse=True)[:8]:
            recent.append({
                "name": node["name"],
                "date": node["date"],
                "mean": round(sum(node["pcts"]) / len(node["pcts"]), 2) if node["pcts"] else 0,
                "subject_count": node["subject_count"],
            })
        # Deviation between consecutive exams (chronological)
        _chrono = sorted(recent, key=lambda x: x["date"])
        for i, r in enumerate(_chrono):
            r["deviation"] = (
                None if i == 0
                else round(r["mean"] - _chrono[i - 1]["mean"], 2)
            )

        return Response({
            "teacher": {
                "id": str(teacher.id),
                "name": f"{teacher.first_name} {teacher.last_name}".strip() or teacher.employee_code,
                "code": teacher.employee_code,
            },
            "overall": {
                "mean": overall,
                "school_mean": school_overall,
                "delta": overall_delta,
                "deviation": (
                    None if len(recent) < 2
                    else round(
                        recent[0]["mean"] - recent[1]["mean"], 2
                    )
                ),
                "std_dev": overall_sd,
                "subject_count": len(subject_rows),
                "class_count": len(class_rows),
                "student_count": len(student_rows),
                "exam_count": len(recent),
                "assessment_coverage_pct": coverage_pct,
                "total_assessments": total_assessments,
                "filled_assessments": filled_assessments,
            },
            "subjects": subject_rows,
            "classes": class_rows,
            "students": student_rows,
            "distribution": overall_dist,
            "strengths": strengths,
            "focus": focus_subj,
            "recent_exams": recent,
        })


class AnalysisTeacherStudentView(_AnalysisBase):
    """
    Drill-down for one student within a teacher's scope.

    Query params:
      ?scope=mine   (default)  -> only the teacher's subjects
      ?scope=whole             -> all subjects in the student's class
    """

    def get(self, request, student_id):
        import statistics as _stats
        from apps.academics.models import (
            Student, StudentEnrollment, Result, ResultStatus,
            InstructionalGroup, Subject, LessonRequirement,
        )
        from apps.users.models import Teacher
        from apps.academics import analysis as A

        u = request.user
        teacher = None
        for attr in ("teacher_profile", "teacher"):
            try:
                v = getattr(u, attr, None)
                if v is not None:
                    teacher = v
                    break
            except Exception:
                pass
        if teacher is None:
            teacher = Teacher.objects.filter(user=u).first()
        if teacher is None:
            return Response({"detail": "No teacher profile linked."}, status=404)

        scope = (request.query_params.get("scope") or "mine").lower()
        if scope not in ("mine", "whole"):
            scope = "mine"

        try:
            student = Student.objects.get(id=student_id)
        except (Student.DoesNotExist, ValueError):
            return Response({"detail": "Student not found."}, status=404)

        direct_lr_ids = set(
            LessonRequirement.objects.filter(teacher=teacher, is_active=True)
            .values_list("id", flat=True)
        )
        assignment_lr_ids = set()
        try:
            from apps.scheduling.models import TeacherAssignment
            assignment_lr_ids = set(
                TeacherAssignment.objects.filter(teacher=teacher, is_active=True)
                .values_list("lesson_requirement_id", flat=True)
            )
        except Exception:
            pass
        combined_lr_ids = direct_lr_ids | assignment_lr_ids
        teacher_lrs = list(
            LessonRequirement.objects.filter(id__in=combined_lr_ids, is_active=True)
            .select_related("subject", "instructional_group")
        )
        teacher_subject_ids = set(lr.subject_id for lr in teacher_lrs if lr.subject_id)

        enrollments = list(
            StudentEnrollment.objects.filter(student=student, is_current=True)
            .select_related("teaching_group")
        )
        if not enrollments:
            return Response({"detail": "Student has no current enrollment."}, status=404)
        enrollment = enrollments[0]
        teaching_group = enrollment.teaching_group

        class_igs = list(
            InstructionalGroup.objects.filter(teaching_group=teaching_group)
        )
        class_ig_ids = [ig.id for ig in class_igs]

        class_lrs = list(
            LessonRequirement.objects.filter(
                instructional_group_id__in=class_ig_ids, is_active=True
            ).select_related("subject", "instructional_group")
        )
        class_subject_ids = set(lr.subject_id for lr in class_lrs if lr.subject_id)

        if scope == "mine":
            include_subject_ids = teacher_subject_ids & class_subject_ids
        else:
            include_subject_ids = class_subject_ids

        results = list(
            Result.objects.filter(
                student=student,
                subject_id__in=include_subject_ids,
                status=ResultStatus.VALID,
            ).select_related("assessment", "subject")
        )

        scheme = A._active_scheme()

        by_subject = {}
        for r in results:
            pct = A._pct(r.raw_mark, r.assessment.max_mark)
            if pct is None:
                continue
            grade = (A.grade_for(scheme, pct) or {}).get("grade", "\u2014")
            sid = str(r.subject_id)
            node = by_subject.setdefault(sid, {
                "subject_id": sid,
                "code": r.subject.code,
                "name": r.subject.name,
                "exams": [],
                "in_scope": r.subject_id in teacher_subject_ids,
            })
            node["exams"].append({
                "assessment_id": str(r.assessment_id),
                "name": r.assessment.name,
                "date": r.assessment.date.isoformat() if r.assessment.date else "",
                "pct": round(pct, 2),
                "grade": grade,
            })

        subject_rows = []
        for sid, node in by_subject.items():
            exams = sorted(node["exams"], key=lambda x: x["date"])
            pcts = [e["pct"] for e in exams]
            if not pcts:
                continue
            mean = round(sum(pcts) / len(pcts), 2)
            grade = (A.grade_for(scheme, mean) or {}).get("grade", "\u2014")
            sd = round(_stats.pstdev(pcts), 2) if len(pcts) >= 2 else 0.0
            trend = "stable"
            if len(pcts) >= 2:
                d = pcts[-1] - pcts[0]
                trend = "improving" if d > 3 else "declining" if d < -3 else "stable"
            subject_rows.append({
                "subject_id": sid,
                "code": node["code"],
                "name": node["name"],
                "mean": mean,
                "grade": grade,
                "sd": sd,
                "trend": trend,
                "exam_count": len(exams),
                "in_scope": node["in_scope"],
                "exams": exams,
            })
        subject_rows.sort(key=lambda x: -x["mean"])

        all_pcts = [e["pct"] for s in subject_rows for e in s["exams"]]
        overall = round(sum(all_pcts) / len(all_pcts), 2) if all_pcts else 0

        return Response({
            "student": {
                "id": str(student.id),
                "name": student.full_name,
                "admission": getattr(student, "admission_number", ""),
                "class_id": str(teaching_group.id) if teaching_group else None,
                "class_name": teaching_group.name if teaching_group else None,
            },
            "scope": scope,
            "overall": {
                "mean": overall,
                "subject_count": len(subject_rows),
                "exam_count": max((s["exam_count"] for s in subject_rows), default=0),
            },
            "subjects": subject_rows,
        })


class AnalysisSchoolView(_AnalysisBase):
    """
    Whole-school analytics with filters.

    Query params:
      ?class=<group_id>   ?stream=<stream_id>   ?student=<id>
      ?subject=<id>       ?teacher=<id>         ?term=<term_id>

    Admin-only (is_staff or is_superuser).
    """

    def get(self, request):
        import statistics as _stats
        from apps.academics.models import (
            Student, StudentEnrollment, Result, ResultStatus,
            InstructionalGroup, Subject, LessonRequirement,
            TeachingGroup, Assessment,
        )
        from apps.core.models import Term
        from apps.academics import analysis as A

        u = request.user
        if not (u and getattr(u, "is_authenticated", False)
                and (u.is_staff or u.is_superuser)):
            return Response({"detail": "Admin access required."}, status=403)

        qp = request.query_params
        f_class = qp.get("class")
        f_stream = qp.get("stream")
        f_student = qp.get("student")
        f_subject = qp.get("subject")
        f_teacher = qp.get("teacher")
        f_term = qp.get("term")

        scheme = A._active_scheme()

        # ---- Base query ----------
        results = Result.objects.filter(status=ResultStatus.VALID).values(
            "id", "student_id", "subject_id", "assessment_id", "raw_mark",
            "assessment__date", "assessment__name", "assessment__max_mark",
            "assessment__term_id",
            "subject__code", "subject__name",
        )

        if f_term:
            results = results.filter(assessment__term_id=f_term)

        if f_subject:
            results = results.filter(subject_id=f_subject)

        if f_student:
            results = results.filter(student_id=f_student)

        if f_class:
            student_ids = list(
                StudentEnrollment.objects.filter(
                    teaching_group_id=f_class, is_current=True
                ).values_list("student_id", flat=True)
            )
            results = results.filter(student_id__in=student_ids)

        if f_stream:
            tg_ids = list(
                TeachingGroup.objects.filter(stream_id=f_stream)
                .values_list("id", flat=True)
            )
            student_ids = list(
                StudentEnrollment.objects.filter(
                    teaching_group_id__in=tg_ids, is_current=True
                ).values_list("student_id", flat=True)
            )
            results = results.filter(student_id__in=student_ids)

        if f_teacher:
            from apps.users.models import Teacher
            from apps.scheduling.models import TeacherAssignment
            try:
                teacher = Teacher.objects.get(id=f_teacher)
            except Teacher.DoesNotExist:
                return Response({"detail": "Teacher not found."}, status=404)
            direct = set(
                LessonRequirement.objects.filter(teacher=teacher, is_active=True)
                .values_list("id", flat=True)
            )
            assigned = set(
                TeacherAssignment.objects.filter(teacher=teacher, is_active=True)
                .values_list("lesson_requirement_id", flat=True)
            )
            lr_ids = direct | assigned
            subj_ids = set(
                LessonRequirement.objects.filter(id__in=lr_ids)
                .values_list("subject_id", flat=True)
            )
            results = results.filter(subject_id__in=subj_ids)

        results = list(results)

        # ---- Overall ----------
        all_pcts = [
            A._pct(r["raw_mark"], r["assessment__max_mark"]) for r in results
        ]
        all_pcts = [p for p in all_pcts if p is not None]
        overall_mean = round(sum(all_pcts) / len(all_pcts), 2) if all_pcts else 0

        student_ids_set = {r["student_id"] for r in results}
        subject_ids_set = {r["subject_id"] for r in results}

        # ---- Deviation helper: previous exam mean vs current ----------
        def _deviation_from_assessments(assessment_ids_and_means):
            """assessment_ids_and_means: list of (date, mean).
            Returns mean of all except the last, and delta of last - that."""
            if len(assessment_ids_and_means) < 2:
                return None
            ordered = sorted(assessment_ids_and_means, key=lambda x: x[0])
            prior = ordered[:-1]
            current = ordered[-1]
            prior_mean = sum(m for _, m in prior) / len(prior)
            return round(current[1] - prior_mean, 2)

        def _by_subject(rows):
            buckets = {}
            for r in rows:
                pct = A._pct(r["raw_mark"], r["assessment__max_mark"])
                if pct is None:
                    continue
                buckets.setdefault(str(r["subject_id"]), {}).setdefault(
                    r["assessment_id"], {"date": r["assessment__date"], "pcts": []}
                )["pcts"].append(pct)
            subject_lookup = {str(s.id): s for s in Subject.objects.filter(id__in=list(buckets.keys()))}
            out = []
            for sid, exams in buckets.items():
                subj = subject_lookup.get(str(sid))
                if not subj:
                    continue
                exam_means = []
                for aid, node in exams.items():
                    m = sum(node["pcts"]) / len(node["pcts"])
                    exam_means.append((node["date"], round(m, 2)))
                all_m = [m for _, m in exam_means]
                mean = round(sum(all_m) / len(all_m), 2)
                dev = _deviation_from_assessments(exam_means)
                out.append({
                    "subject_id": sid,
                    "code": subj.code,
                    "name": subj.name,
                    "mean": mean,
                    "deviation": dev,
                    "exam_count": len(exam_means),
                    "student_count": len({
                        r["student_id"] for r in rows if str(r["subject_id"]) == sid
                    }),
                })
            out.sort(key=lambda x: -x["mean"])
            for i, row in enumerate(out, 1):
                row["rank"] = i
            return out

        def _by_class(rows):
            stu_to_groups = {}
            for sid, tg in StudentEnrollment.objects.filter(
                is_current=True
            ).values_list("student_id", "teaching_group_id"):
                stu_to_groups.setdefault(str(sid), set()).add(str(tg))
            buckets = {}
            for r in rows:
                pct = A._pct(r["raw_mark"], r["assessment__max_mark"])
                if pct is None:
                    continue
                for gid in stu_to_groups.get(str(r["student_id"]), ()):
                    buckets.setdefault(gid, {}).setdefault(
                        r["assessment_id"], {"date": r["assessment__date"], "pcts": []}
                    )["pcts"].append(pct)
            tg_lookup = {str(tg.id): tg for tg in TeachingGroup.objects.filter(id__in=list(buckets.keys()))}
            out = []
            for gid, exams in buckets.items():
                tg = tg_lookup.get(str(gid))
                if not tg:
                    continue
                exam_means = []
                for aid, node in exams.items():
                    m = sum(node["pcts"]) / len(node["pcts"])
                    exam_means.append((node["date"], round(m, 2)))
                all_m = [m for _, m in exam_means]
                mean = round(sum(all_m) / len(all_m), 2)
                dev = _deviation_from_assessments(exam_means)
                out.append({
                    "group_id": gid,
                    "group_name": tg.name,
                    "mean": mean,
                    "deviation": dev,
                    "exam_count": len(exam_means),
                    "student_count": StudentEnrollment.objects.filter(
                        teaching_group_id=gid, is_current=True
                    ).count(),
                })
            out.sort(key=lambda x: -x["mean"])
            for i, row in enumerate(out, 1):
                row["rank"] = i
            return out

        def _by_teacher(rows):
            # -----------------------------------------------------------------
            # PERFORMANCE: this used to iterate `rows` twice for every teacher
            # (24 ? 22k ? 2 = ~1M iterations ? ~20s). Now we preload the
            # teacher?subject map in two queries and iterate `rows` once,
            # touching only the teachers who actually teach each subject.
            # -----------------------------------------------------------------
            from apps.users.models import Teacher
            from apps.scheduling.models import TeacherAssignment
            from collections import defaultdict

            teachers = list(Teacher.objects.all())
            teacher_by_id = {t.id: t for t in teachers}

            # teacher_id -> set(subject_id)
            teacher_subjects = defaultdict(set)

            # Direct LessonRequirement assignments
            for t_id, subj_id in (
                LessonRequirement.objects
                .filter(is_active=True, teacher_id__isnull=False)
                .values_list("teacher_id", "subject_id")
            ):
                if subj_id:
                    teacher_subjects[t_id].add(subj_id)

            # Scheduling TeacherAssignment side
            for t_id, subj_id in (
                TeacherAssignment.objects
                .filter(is_active=True)
                .values_list("teacher_id", "lesson_requirement__subject_id")
            ):
                if subj_id:
                    teacher_subjects[t_id].add(subj_id)

            # Invert: subject_id -> set(teacher_id)
            subject_to_teachers = defaultdict(set)
            for t_id, subjs in teacher_subjects.items():
                for s in subjs:
                    subject_to_teachers[s].add(t_id)

            # One pass over rows; update only the affected teachers.
            per_teacher_pcts = defaultdict(list)
            per_teacher_by_assessment = defaultdict(lambda: defaultdict(list))
            per_teacher_students = defaultdict(set)

            for r in rows:
                if r["subject_id"] is None:
                    continue
                pct = A._pct(r["raw_mark"], r["assessment__max_mark"])
                if pct is None:
                    continue
                for t_id in subject_to_teachers.get(r["subject_id"], ()):
                    per_teacher_pcts[t_id].append(pct)
                    per_teacher_by_assessment[t_id][r["assessment_id"]].append(
                        (r["assessment__date"], pct)
                    )
                    per_teacher_students[t_id].add(r["student_id"])

            buckets = {}
            for t_id, pcts in per_teacher_pcts.items():
                t = teacher_by_id.get(t_id)
                if t is None or not pcts:
                    continue
                exam_means = []
                for aid, plist in per_teacher_by_assessment[t_id].items():
                    avg = sum(p for _, p in plist) / len(plist)
                    date = plist[0][0]
                    exam_means.append((date, round(avg, 2)))
                dev = _deviation_from_assessments(exam_means)
                buckets[str(t_id)] = {
                    "teacher_id": str(t_id),
                    "name": (f"{t.first_name} {t.last_name}".strip()
                             or t.employee_code),
                    "code": t.employee_code,
                    "mean": round(sum(pcts) / len(pcts), 2),
                    "deviation": dev,
                    "student_count": len(per_teacher_students[t_id]),
                    "subject_count": len(teacher_subjects[t_id]),
                }

            out = sorted(buckets.values(), key=lambda x: -x["mean"])
            for i, row in enumerate(out, 1):
                row["rank"] = i
            return out

        def _by_term(rows):
            from apps.core.models import Term as _Term
            term_lookup = {t.id: t for t in _Term.objects.all()}
            buckets = {}
            for r in rows:
                pct = A._pct(r["raw_mark"], r["assessment__max_mark"])
                if pct is None:
                    continue
                t_id = r.get("assessment__term_id")
                t = term_lookup.get(t_id) if t_id else None
                if not t:
                    continue
                buckets.setdefault(str(t.id), {
                    "term_id": str(t.id),
                    "name": t.name,
                    "pcts": [],
                })["pcts"].append(pct)
            ordered = sorted(buckets.values(), key=lambda x: x["name"])
            out = []
            prev_mean = None
            for node in ordered:
                m = round(sum(node["pcts"]) / len(node["pcts"]), 2)
                dev = round(m - prev_mean, 2) if prev_mean is not None else None
                out.append({
                    "term_id": node["term_id"],
                    "name": node["name"],
                    "mean": m,
                    "deviation": dev,
                    "exam_count": len(node["pcts"]),
                })
                prev_mean = m
            return out

        by_subject = _by_subject(results)
        by_class = _by_class(results)
        by_teacher = _by_teacher(results)
        by_term = _by_term(results)

        # Stream aggregation from by_class (map group → stream)
        tg_stream_map = {
            str(tg.id): {"stream_id": str(tg.stream_id) if tg.stream_id else None,
                         "stream_name": tg.stream.name if tg.stream else None}
            for tg in TeachingGroup.objects.select_related("stream").all()
        }
        stream_buckets = {}
        for row in by_class:
            s = tg_stream_map.get(row["group_id"], {})
            sid = s.get("stream_id")
            if not sid:
                continue
            b = stream_buckets.setdefault(sid, {
                "stream_id": sid,
                "stream_name": s["stream_name"],
                "means": [],
                "student_count": 0,
            })
            b["means"].append(row["mean"])
            b["student_count"] += row["student_count"]
        by_stream = []
        for sid, b in stream_buckets.items():
            if not b["means"]:
                continue
            by_stream.append({
                "stream_id": sid,
                "stream_name": b["stream_name"],
                "mean": round(sum(b["means"]) / len(b["means"]), 2),
                "student_count": b["student_count"],
                "class_count": len(b["means"]),
            })
        by_stream.sort(key=lambda x: -x["mean"])

        # Recent exams across school
        exam_map = {}
        for r in results:
            pct = A._pct(r["raw_mark"], r["assessment__max_mark"])
            if pct is None:
                continue
            key = str(r["assessment_id"])
            node = exam_map.setdefault(key, {
                "assessment_id": key,
                "name": r["assessment__name"],
                "date": r["assessment__date"].isoformat() if r["assessment__date"] else "",
                "pcts": [],
            })
            node["pcts"].append(pct)
        recent = []
        for node in sorted(exam_map.values(), key=lambda x: x["date"], reverse=True)[:8]:
            recent.append({
                "assessment_id": node["assessment_id"],
                "name": node["name"],
                "date": node["date"],
                "mean": round(sum(node["pcts"]) / len(node["pcts"]), 2) if node["pcts"] else 0,
                "subject_count": len(node["pcts"]),
            })

        return Response({
            "filters": {
                "class": f_class, "stream": f_stream, "student": f_student,
                "subject": f_subject, "teacher": f_teacher, "term": f_term,
            },
            "overall": {
                "mean": overall_mean,
                "student_count": len(student_ids_set),
                "subject_count": len(subject_ids_set),
                "class_count": len(by_class),
                "teacher_count": len(by_teacher),
                "exam_count": len(recent),
            },
            "by_class": by_class,
            "by_stream": by_stream,
            "by_subject": by_subject,
            "by_teacher": by_teacher,
            "by_term": by_term,
            "recent_exams": recent,
        })


class AnalysisSchoolFiltersView(_AnalysisBase):
    """Return dropdown lists for the school analytics filter bar. Admin-only."""

    def get(self, request):
        from apps.academics.models import (
            TeachingGroup, Stream, Subject, Student,
        )
        from apps.core.models import Term
        from apps.users.models import Teacher

        u = request.user
        if not (u and getattr(u, "is_authenticated", False)
                and (u.is_staff or u.is_superuser)):
            return Response({"detail": "Admin access required."}, status=403)

        classes = [
            {"id": str(tg.id), "name": tg.name}
            for tg in TeachingGroup.objects.filter(is_active=True).order_by("name")
        ]
        streams = [
            {"id": str(s.id), "name": s.name}
            for s in Stream.objects.all().order_by("name")
        ]
        subjects = [
            {"id": str(s.id), "name": s.name, "code": s.code}
            for s in Subject.objects.filter(is_active=True).order_by("name")
        ]
        teachers = [
            {"id": str(t.id),
             "name": (f"{t.first_name} {t.last_name}".strip() or t.employee_code),
             "code": t.employee_code}
            for t in Teacher.objects.filter(is_active=True).order_by("last_name", "first_name")
        ]
        terms = [
            {"id": str(t.id), "name": t.name}
            for t in Term.objects.all().order_by("academic_year", "number")
        ]
        # Limit students list for the dropdown (only active, ordered)
        students = [
            {"id": str(s.id), "name": s.full_name,
             "admission": getattr(s, "admission_number", "")}
            for s in Student.objects.filter(is_active=True)
            .order_by("last_name", "first_name")[:1000]
        ]

        return Response({
            "classes": classes,
            "streams": streams,
            "subjects": subjects,
            "teachers": teachers,
            "terms": terms,
            "students": students,
        })


class ReportFormView(_AnalysisBase):
    def get(self, request, student_id):
        from apps.academics.models import Student
        try:
            Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"detail": "Student not found"}, status=404)
        return Response(_attach_comments(_analysis.report_form(student_id)))



class ReportFormBulkView(_AnalysisBase):
    """
    GET /api/academics/analysis/report-form-bulk/?teaching_group=<uuid>
    Returns report forms for all current students in the class,
    ordered by rank (best first).
    """
    def get(self, request):
        from apps.academics.models import (
            Student, StudentEnrollment, Result, ResultStatus,
        )
        import statistics as _stats

        tg_id = request.query_params.get("teaching_group")
        if not tg_id:
            return Response({"detail": "teaching_group required"}, status=400)

        enrollments = (
            StudentEnrollment.objects
            .filter(teaching_group_id=tg_id, is_current=True)
            .select_related("student", "teaching_group")
        )
        students = [e.student for e in enrollments]
        if not students:
            return Response({"students": [], "class_name": None, "count": 0})

        # Rank all students in the class by mean across all results
        student_means = {}
        for s in students:
            rs = Result.objects.filter(student=s, status=ResultStatus.VALID).select_related("assessment")
            pcts = []
            for r in rs:
                pct = _analysis._pct(r.raw_mark, r.assessment.max_mark)
                if pct is not None:
                    pcts.append(pct)
            if pcts:
                student_means[s.id] = _stats.mean(pcts)

        ranked = sorted(students, key=lambda s: -student_means.get(s.id, -1))

        forms = []
        for s in ranked:
            try:
                forms.append(_attach_comments(_analysis.report_form(s.id)))
            except Exception as e:
                forms.append({
                    "student": {"id": str(s.id), "name": s.full_name, "admission_number": s.admission_number},
                    "error": str(e),
                })

        class_name = enrollments[0].teaching_group.name if enrollments else None
        return Response({
            "class_name": class_name,
            "count": len(forms),
            "students": forms,
        })

from apps.academics.audit_util import log_event as _log_audit_event



# ---------------------------------------------------------------------
# Audit trail viewset (RoE §26)
# ---------------------------------------------------------------------
from apps.academics.serializers import (
    AcademicAuditEventSerializer as _AuditSer,
)
from apps.academics.models import AcademicAuditEvent as _AuditModel


class AcademicAuditViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only audit log.

    Query params:
      ?entity_type=Result|Assessment|Student|GradingScheme
      ?action=PUBLISH|BULK_UPDATE|...
      ?actor=<username>
      ?from=YYYY-MM-DD  ?to=YYYY-MM-DD
      ?q=<substring of entity_label>
    """
    queryset = _AuditModel.objects.all()
    serializer_class = _AuditSer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["entity_label", "entity_type", "action"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("actor")
        et = self.request.query_params.get("entity_type")
        ac = self.request.query_params.get("action")
        actor = self.request.query_params.get("actor")
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")
        if et:
            qs = qs.filter(entity_type=et)
        if ac:
            qs = qs.filter(action=ac)
        if actor:
            qs = qs.filter(actor__username=actor)
        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)
        return qs



# ---------------------------------------------------------------------
# Comments + Grading scheme CRUD (added 2026-09-17)
# ---------------------------------------------------------------------
from apps.academics.models import (
    ReportComment as _RC_Model,
    GradingScheme as _GS_Model,
    GradingBand as _GB_Model,
)
from apps.academics.serializers import (
    ReportCommentSerializer as _RC_Ser,
    GradingSchemeSerializer as _GS_Ser,
    GradingBandSerializer as _GB_Ser,
)


class ReportCommentViewSet(viewsets.ModelViewSet):
    queryset = _RC_Model.objects.select_related("student", "term", "academic_year")
    serializer_class = _RC_Ser
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        ids = teacher_student_ids(self.request.user)
        if ids is None:
            return qs
        return qs.filter(student_id__in=ids)

    @action(detail=False, methods=["post"], url_path="upsert")
    def upsert(self, request):
        sid = request.data.get("student")
        ay = request.data.get("academic_year")
        tid = request.data.get("term")
        if not (sid and ay and tid):
            return Response(
                {"detail": "student, academic_year, term required"},
                status=400,
            )
        _ids = teacher_student_ids(request.user)
        if _ids is not None and str(sid) not in {str(x) for x in _ids}:
            return Response(
                {"detail": "You cannot comment on a student you do not teach."},
                status=403,
            )
        _admin = is_admin_like(request.user)
        _defaults = {
            "conduct": request.data.get("conduct", ""),
            "class_teacher_comment": request.data.get("class_teacher_comment", ""),
        }
        if _admin:
            _defaults["rector_comment"] = request.data.get("rector_comment", "")
            _defaults["mission_comment"] = request.data.get("mission_comment", "")
        obj, created = _RC_Model.objects.update_or_create(
            student_id=sid, academic_year_id=ay, term_id=tid,
            defaults=_defaults,
        )
        return Response(_RC_Ser(obj).data, status=201 if created else 200)


class GradingSchemeViewSet(viewsets.ModelViewSet):
    queryset = _GS_Model.objects.all()
    serializer_class = _GS_Ser
    permission_classes = [IsAuthenticated, CanEditGrading]

    def _invalidate(self):
        try:
            from apps.academics.analysis import invalidate_grading_cache
            invalidate_grading_cache()
        except Exception:
            pass

    def perform_create(self, serializer):
        serializer.save()
        self._invalidate()

    def perform_update(self, serializer):
        serializer.save()
        self._invalidate()

    def perform_destroy(self, instance):
        instance.delete()
        self._invalidate()


class GradingBandViewSet(viewsets.ModelViewSet):
    queryset = _GB_Model.objects.all()
    serializer_class = _GB_Ser
    permission_classes = [IsAuthenticated, CanEditGrading]

    def _invalidate(self):
        try:
            from apps.academics.analysis import invalidate_grading_cache
            invalidate_grading_cache()
        except Exception:
            pass

    def perform_create(self, serializer):
        serializer.save()
        self._invalidate()

    def perform_update(self, serializer):
        serializer.save()
        self._invalidate()

    def perform_destroy(self, instance):
        instance.delete()
        self._invalidate()



# ---------------------------------------------------------------------
# Comment attachment for report forms (added 2026-09-17)
# ---------------------------------------------------------------------
def _attach_comments(form):
    from apps.academics.models import ReportComment
    from apps.core.models import Term
    empty = {
        "conduct": "",
        "class_teacher_comment": "",
        "rector_comment": "",
        "mission_comment": "",
    }
    sid = (form.get("student") or {}).get("id")
    if not sid:
        form["comments"] = empty
        return form
    term = Term.objects.filter(is_active=True).first()
    ay_id = getattr(term, "academic_year_id", None) if term else None
    if not (term and ay_id):
        form["comments"] = empty
        return form
    c = ReportComment.objects.filter(
        student_id=sid, term=term, academic_year_id=ay_id,
    ).first()
    if c:
        form["comments"] = {
            "conduct": c.conduct,
            "class_teacher_comment": c.class_teacher_comment,
            "rector_comment": c.rector_comment,
            "mission_comment": c.mission_comment,
        }
    else:
        form["comments"] = empty
    return form



# ---------------------------------------------------------------------
# Ranking rules + runs (RoE §17-18)
# ---------------------------------------------------------------------
from apps.academics.models import (
    RankingRule as _RR_Model,
    RankingRun as _RRun_Model,
)
from apps.academics.serializers import (
    RankingRuleSerializer as _RR_Ser,
    RankingRunSerializer as _RRun_Ser,
)


class RankingRuleViewSet(viewsets.ModelViewSet):
    queryset = _RR_Model.objects.all()
    serializer_class = _RR_Ser
    permission_classes = [IsAdminLike]

    def perform_update(self, serializer):
        old = self.get_object()
        instance = serializer.save(version=old.version + 1)
        try:
            from apps.academics.audit_util import log_event as _log
            _log(
                self.request,
                action="UPDATE",
                entity_type="RankingRule",
                entity_label=instance.name,
                entity_id=instance.id,
                meta={"old_version": old.version, "new_version": instance.version},
            )
        except Exception:
            pass

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            from apps.academics.audit_util import log_event as _log
            _log(
                self.request,
                action="CREATE",
                entity_type="RankingRule",
                entity_label=instance.name,
                entity_id=instance.id,
            )
        except Exception:
            pass


class RankingRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = _RRun_Model.objects.all().select_related("rule")
    serializer_class = _RRun_Ser
    permission_classes = [IsAuthenticated]


class RankingPreviewView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        rule_id = request.query_params.get("rule")
        assessment_id = request.query_params.get("assessment")
        teaching_group_id = request.query_params.get("teaching_group")
        persist = request.query_params.get("persist") in ("1", "true", "yes")
        if not rule_id:
            return Response({"detail": "rule required"}, status=400)
        try:
            data = _analysis.compute_ranking(
                rule_id=rule_id,
                assessment_id=assessment_id,
                teaching_group_id=teaching_group_id,
                persist=persist,
                request=request,
            )
        except _RR_Model.DoesNotExist:
            return Response({"detail": "rule not found"}, status=404)
        return Response(data)



# ---------------------------------------------------------------------
# Marks entry context (classes + subjects by class, role-aware)
# ---------------------------------------------------------------------
class MarksEntryContextView(APIView):
    """
    Returns classes the user can enter marks for, and the subjects
    available in each. Non-admin teachers are restricted to subjects
    that appear in LessonRequirements assigned to them; if none are
    assigned, they fall back to all subjects taught in that class.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.academics.models import (
            TeachingGroup, Subject, LessonRequirement, InstructionalGroup,
        )
        from apps.academics.teacher_scope import (
            is_admin_like, teacher_record,
        )

        user = request.user
        admin = is_admin_like(user)
        teacher = None if admin else teacher_record(user)

        if admin:
            # Admin: all active teaching groups
            tg_ids = list(
                TeachingGroup.objects.filter(is_active=True)
                .order_by("name")
                .values_list("id", flat=True)
            )
        elif teacher is not None:
            # Teacher: only the teaching groups of classes they handle
            ig_ids = list(
                LessonRequirement.objects.filter(teacher=teacher, is_active=True)
                .values_list("instructional_group_id", flat=True)
                .distinct()
            )
            tg_ids = list(
                InstructionalGroup.objects.filter(id__in=ig_ids)
                .values_list("teaching_group_id", flat=True)
                .distinct()
            )
        else:
            tg_ids = []

        classes_qs = (
            TeachingGroup.objects.filter(id__in=tg_ids)
            .order_by("name")
            .values("id", "name")
        )
        classes = [{"id": str(c["id"]), "name": c["name"]} for c in classes_qs]

        subjects_by_class = {}
        for c in classes:
            cid = c["id"]
            if admin:
                # All subjects taught in this class
                subj_ids = set(
                    str(x)
                    for x in LessonRequirement.objects.filter(
                        instructional_group__teaching_group_id=cid,
                        is_active=True,
                    ).values_list("subject_id", flat=True)
                )
            else:
                # Only subjects this teacher teaches in this class
                subj_ids = set(
                    str(x)
                    for x in LessonRequirement.objects.filter(
                        instructional_group__teaching_group_id=cid,
                        teacher=teacher,
                        is_active=True,
                    ).values_list("subject_id", flat=True)
                )
            if not subj_ids:
                subjects_by_class[cid] = []
                continue
            qs = Subject.objects.filter(id__in=subj_ids, is_active=True).order_by("name")
            subjects_by_class[cid] = [
                {"id": str(s.id), "name": s.name, "code": s.code}
                for s in qs
            ]

        return Response({
            "is_admin": admin,
            "teacher_name": (
                f"{teacher.first_name} {teacher.last_name}".strip()
                if teacher else None
            ),
            "classes": classes,
            "subjects_by_class": subjects_by_class,
        })



class StreamSummaryView(_AnalysisBase):
    def get(self, request):
        try:
            from apps.academics.teacher_scope import (
                teacher_classes, teacher_subject_ids, teacher_student_ids,
                is_admin_like,
            )
            scope_whole = (request.query_params.get("scope") or "").lower() == "whole"
            scope_classes = None if (is_admin_like(request.user) or scope_whole) else set(teacher_classes(request.user).values_list("id", flat=True))
            scope_subjects = None if (is_admin_like(request.user) or scope_whole) else teacher_subject_ids(request.user)
            scope_students = None if (is_admin_like(request.user) or scope_whole) else teacher_student_ids(request.user)
            aid = request.query_params.get("assessment")
            tgid = request.query_params.get("stream")
            if not aid or not tgid:
                return Response({"detail": "assessment and stream required"}, status=400)
            try:
                data = _analysis.stream_summary(aid, tgid)
            except _Assessment.DoesNotExist:
                return Response({"detail": "assessment not found"}, status=404)
            return Response(data)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("StreamSummaryView failed")
            return Response({
                "detail": "Could not load the stream report.",
                "hint": "Please try again. If it persists, contact your administrator.",
                "code": "STREAM_SUMMARY_FAILED",
            }, status=500)



class StreamTrendView(_AnalysisBase):
    def get(self, request):
        try:
            from apps.academics.teacher_scope import (
                teacher_classes, teacher_subject_ids, teacher_student_ids,
                is_admin_like,
            )
            scope_whole = (request.query_params.get("scope") or "").lower() == "whole"
            scope_classes = None if (is_admin_like(request.user) or scope_whole) else set(teacher_classes(request.user).values_list("id", flat=True))
            scope_subjects = None if (is_admin_like(request.user) or scope_whole) else teacher_subject_ids(request.user)
            scope_students = None if (is_admin_like(request.user) or scope_whole) else teacher_student_ids(request.user)
            tgid = request.query_params.get("stream")
            if not tgid:
                return Response({"detail": "stream required"}, status=400)
            limit = int(request.query_params.get("limit", "3"))
            return Response(_analysis.stream_trend(tgid, assessment_limit=limit))
        except Exception:
            import logging
            logging.getLogger(__name__).exception("StreamTrendView failed")
            return Response({
                "detail": "Could not load the stream trend.",
                "hint": "Please try again. If it persists, contact your administrator.",
                "code": "STREAM_TREND_FAILED",
            }, status=500)


