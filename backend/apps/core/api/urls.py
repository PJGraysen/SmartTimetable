from django.urls import path

from .views import (
    AcademicYearDetailView,
    AcademicYearListCreateView,
    SchoolDetailView,
    SchoolListCreateView,
    TermDetailView,
    TermListCreateView,
)


urlpatterns = [
    path(
        "schools/",
        SchoolListCreateView.as_view(),
        name="school-list-create",
    ),
    path(
        "schools/<uuid:pk>/",
        SchoolDetailView.as_view(),
        name="school-detail",
    ),

    path(
        "academic-years/",
        AcademicYearListCreateView.as_view(),
        name="academic-year-list-create",
    ),
    path(
        "academic-years/<uuid:pk>/",
        AcademicYearDetailView.as_view(),
        name="academic-year-detail",
    ),

    path(
        "terms/",
        TermListCreateView.as_view(),
        name="term-list-create",
    ),
    path(
        "terms/<uuid:pk>/",
        TermDetailView.as_view(),
        name="term-detail",
    ),
]
