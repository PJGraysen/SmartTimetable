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
    permission_classes = [AllowAny]


class AnalysisAssessmentsView(_AnalysisBase):
    def get(self, request):
        return Response(_analysis.list_assessments())


class AnalysisDashboardView(_AnalysisBase):
    def get(self, request):
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
        return Response(data)


class AnalysisStudentView(_AnalysisBase):
    def get(self, request, student_id):
        from apps.academics.models import Student, Result, ResultStatus
        try:
            s = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"detail": "Student not found"}, status=404)
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
            Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"detail": "Student not found"}, status=404)
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
    permission_classes = [AllowAny]

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
    permission_classes = [AllowAny]

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

        students = _Student.objects.filter(is_active=True).order_by("last_name", "first_name")
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
            return Response({"detail": "not found"}, status=404)

        # Bulk marks gating
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

        created = 0
        updated = 0
        for row in ser.validated_data["marks"]:
            student_id = row.get("student") or row.get("student_id")
            raw = row.get("raw_mark")
            stat = row.get("status", "VALID")
            if (raw is None or raw == "") and stat == "VALID":
                stat = "MISSING"
            if not student_id:
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
        return Response(data)



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
    permission_classes = [AllowAny]

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
        obj, created = _RC_Model.objects.update_or_create(
            student_id=sid, academic_year_id=ay, term_id=tid,
            defaults={
                "conduct": request.data.get("conduct", ""),
                "class_teacher_comment": request.data.get("class_teacher_comment", ""),
                "rector_comment": request.data.get("rector_comment", ""),
                "mission_comment": request.data.get("mission_comment", ""),
            },
        )
        return Response(_RC_Ser(obj).data, status=201 if created else 200)


class GradingSchemeViewSet(viewsets.ModelViewSet):
    queryset = _GS_Model.objects.all()
    serializer_class = _GS_Ser
    permission_classes = [AllowAny]


class GradingBandViewSet(viewsets.ModelViewSet):
    queryset = _GB_Model.objects.all()
    serializer_class = _GB_Ser
    permission_classes = [AllowAny]



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
    permission_classes = [AllowAny]

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
    permission_classes = [AllowAny]


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
            TeachingGroup, Subject, LessonRequirement,
        )
        user = request.user
        is_admin = bool(user and getattr(user, "is_authenticated", False)
                        and (user.is_superuser or user.is_staff))
        teacher = None
        if user and getattr(user, "is_authenticated", False) and not is_admin:
            teacher = getattr(user, "teacher_profile", None)

        classes = list(
            TeachingGroup.objects.filter(is_active=True)
            .order_by("name")
            .values("id", "name")
        )
        classes = [{"id": str(c["id"]), "name": c["name"]} for c in classes]

        subjects_by_class = {}
        for c in classes:
            cid = c["id"]
            lrs = LessonRequirement.objects.filter(
                instructional_group__teaching_group_id=cid,
                is_active=True,
            )
            subj_ids_class = set(str(x.subject_id) for x in lrs)
            if teacher is not None:
                subj_ids_teacher = set(
                    str(x.subject_id)
                    for x in lrs.filter(teacher=teacher)
                )
                if subj_ids_teacher:
                    subj_ids_class = subj_ids_teacher

            qs = Subject.objects.filter(id__in=subj_ids_class, is_active=True).order_by("name")
            if not qs.exists():
                qs = Subject.objects.filter(is_active=True).order_by("name")
            subjects_by_class[cid] = [
                {"id": str(s.id), "name": s.name, "code": s.code}
                for s in qs
            ]

        return Response({
            "is_admin": is_admin,
            "teacher_name": (
                f"{teacher.first_name} {teacher.last_name}".strip()
                if teacher else None
            ),
            "classes": classes,
            "subjects_by_class": subjects_by_class,
        })



class StreamSummaryView(_AnalysisBase):
    def get(self, request):
        aid = request.query_params.get("assessment")
        tgid = request.query_params.get("stream")
        if not aid or not tgid:
            return Response({"detail": "assessment and stream required"}, status=400)
        try:
            data = _analysis.stream_summary(aid, tgid)
        except _Assessment.DoesNotExist:
            return Response({"detail": "assessment not found"}, status=404)
        return Response(data)



class StreamTrendView(_AnalysisBase):
    def get(self, request):
        tgid = request.query_params.get("stream")
        if not tgid:
            return Response({"detail": "stream required"}, status=400)
        limit = int(request.query_params.get("limit", "3"))
        return Response(_analysis.stream_trend(tgid, assessment_limit=limit))
