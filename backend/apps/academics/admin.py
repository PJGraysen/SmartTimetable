from django.contrib import admin

from .models import (
    Grade,
    LessonRequirement,
    Stream,
    Subject,
    TeachingGroup,
)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "academic_year",
    )
    list_filter = ("academic_year",)
    search_fields = (
        "name",
        "code",
    )


@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "grade",
    )
    list_filter = (
        "grade",
        "grade__academic_year",
    )
    search_fields = (
        "name",
        "code",
    )


@admin.register(TeachingGroup)
class TeachingGroupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "stream",
        "learner_count",
        "is_active",
    )
    list_filter = (
        "is_active",
        "stream__grade",
    )
    search_fields = (
        "name",
        "code",
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "code",
    )


@admin.register(LessonRequirement)
class LessonRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "term",
        "instructional_group",
        "subject",
        "lessons_per_week",
        "is_active",
    )
    list_filter = (
        "term",
        "is_active",
        "subject",
    )
    search_fields = (
        "instructional_group__name",
        "subject__name",
    )



from django.contrib import admin
from apps.academics.models import Student, StudentEnrollment


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("admission_number", "full_name", "status", "is_active")
    search_fields = ("admission_number", "first_name", "middle_name", "last_name")
    list_filter = ("status", "is_active", "gender")


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "teaching_group", "academic_year", "is_current")
    list_filter = ("is_current", "academic_year", "teaching_group")
    search_fields = ("student__admission_number", "student__last_name")
