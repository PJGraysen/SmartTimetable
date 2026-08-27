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
