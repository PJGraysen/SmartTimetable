from django.urls import path

from .views import (
    GradeDetailView,
    GradeListCreateView,
    InstructionalGroupListView,
    LessonRequirementDetailView,
    LessonRequirementListCreateView,
    StreamDetailView,
    StreamListCreateView,
    SubjectDetailView,
    SubjectListCreateView,
    TeachingGroupDetailView,
    TeachingGroupListCreateView,
)


urlpatterns = [
    path(
        "grades/",
        GradeListCreateView.as_view(),
        name="grade-list-create",
    ),
    path(
        "grades/<uuid:pk>/",
        GradeDetailView.as_view(),
        name="grade-detail",
    ),

    path(
        "instructional-groups/",
        InstructionalGroupListView.as_view(),
        name="instructional-group-list",
    ),

    path(
        "streams/",
        StreamListCreateView.as_view(),
        name="stream-list-create",
    ),
    path(
        "streams/<uuid:pk>/",
        StreamDetailView.as_view(),
        name="stream-detail",
    ),

    path(
        "teaching-groups/",
        TeachingGroupListCreateView.as_view(),
        name="teaching-group-list-create",
    ),
    path(
        "teaching-groups/<uuid:pk>/",
        TeachingGroupDetailView.as_view(),
        name="teaching-group-detail",
    ),

    path(
        "subjects/",
        SubjectListCreateView.as_view(),
        name="subject-list-create",
    ),
    path(
        "subjects/<uuid:pk>/",
        SubjectDetailView.as_view(),
        name="subject-detail",
    ),

    path(
        "lesson-requirements/",
        LessonRequirementListCreateView.as_view(),
        name="lesson-requirement-list-create",
    ),
    path(
        "lesson-requirements/<uuid:pk>/",
        LessonRequirementDetailView.as_view(),
        name="lesson-requirement-detail",
    ),
]



# ---------------------------------------------------------------------
# Student API registration (added 2026-09-16)
# ViewSet lives in apps.academics.views (appended by the seed script).
# ---------------------------------------------------------------------
from rest_framework.routers import DefaultRouter as _StudentDR
from apps.academics.views import StudentViewSet as _StudentVS

_student_router = _StudentDR()
_student_router.register(r"students", _StudentVS, basename="student")

try:
    urlpatterns = list(urlpatterns) + list(_student_router.urls)
except NameError:
    urlpatterns = list(_student_router.urls)



# ---------------------------------------------------------------------
# Analysis API (added 2026-09-16)
# ---------------------------------------------------------------------
from django.urls import path as _apath
from apps.academics.views import (
    AnalysisAssessmentsView as _AAV,
    AnalysisDashboardView as _ADV,
    AnalysisStudentView as _ASV,
)

urlpatterns += [
    _apath("analysis/assessments/", _AAV.as_view(), name="analysis-assessments"),
    _apath("analysis/dashboard/", _ADV.as_view(), name="analysis-dashboard"),
    _apath("analysis/student/<uuid:student_id>/", _ASV.as_view(), name="analysis-student"),
]



from apps.academics.views import AnalysisStudentDeepView as _ASDV
urlpatterns += [
    _apath("analysis/student-deep/<uuid:student_id>/", _ASDV.as_view(), name="analysis-student-deep"),
]



# ---------------------------------------------------------------------
# Assessments + Results routers (added 2026-09-17)
# ---------------------------------------------------------------------
from rest_framework.routers import DefaultRouter as _DR2
from apps.academics.views import (
    AssessmentViewSet as _AVS,
    ResultViewSet as _RVS,
)

_marks_router = _DR2()
_marks_router.register(r"assessments", _AVS, basename="assessment")
_marks_router.register(r"results", _RVS, basename="result")
urlpatterns += _marks_router.urls



from apps.academics.views import AnalysisClassComparisonView as _ACCV
urlpatterns += [
    _apath("analysis/classes/", _ACCV.as_view(), name="analysis-classes"),
]



from apps.academics.views import ReportFormView as _RFV
urlpatterns += [
    _apath("analysis/report-form/<uuid:student_id>/", _RFV.as_view(), name="analysis-report-form"),
]



from apps.academics.views import ReportFormBulkView as _RFBV
urlpatterns += [
    _apath("analysis/report-form-bulk/", _RFBV.as_view(), name="analysis-report-form-bulk"),
]



from rest_framework.routers import DefaultRouter as _DR_Audit
from apps.academics.views import AcademicAuditViewSet as _AuditVS

_audit_router = _DR_Audit()
_audit_router.register(r"audit-events", _AuditVS, basename="audit-event")
urlpatterns += _audit_router.urls



from rest_framework.routers import DefaultRouter as _DR_Extra
from apps.academics.views import (
    ReportCommentViewSet as _RC_VS,
    GradingSchemeViewSet as _GS_VS,
    GradingBandViewSet as _GB_VS,
)

_extra_router = _DR_Extra()
_extra_router.register(r"report-comments", _RC_VS, basename="report-comment")
_extra_router.register(r"grading-schemes", _GS_VS, basename="grading-scheme")
_extra_router.register(r"grading-bands", _GB_VS, basename="grading-band")
urlpatterns += _extra_router.urls



from rest_framework.routers import DefaultRouter as _DR_Rank
from apps.academics.views import (
    RankingRuleViewSet as _RRVS,
    RankingRunViewSet as _RRunVS,
    RankingPreviewView as _RPV,
)

_rank_router = _DR_Rank()
_rank_router.register(r"ranking-rules", _RRVS, basename="ranking-rule")
_rank_router.register(r"ranking-runs", _RRunVS, basename="ranking-run")
urlpatterns += _rank_router.urls
urlpatterns += [
    _apath("ranking/preview/", _RPV.as_view(), name="ranking-preview"),
]
