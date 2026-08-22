from __future__ import annotations

from rest_framework import serializers

from apps.academics.models import (
    Grade,
    Stream,
    TeachingGroup,
    Subject,
    LessonRequirement,
)


class GradeSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(
        source="academic_year.__str__",
        read_only=True,
    )

    class Meta:
        model = Grade
        fields = (
            "id",
            "academic_year",
            "academic_year_name",
            "name",
            "code",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "academic_year_name",
            "created_at",
            "updated_at",
        )


class StreamSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(
        source="grade.__str__",
        read_only=True,
    )

    class Meta:
        model = Stream
        fields = (
            "id",
            "grade",
            "grade_name",
            "name",
            "code",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "grade_name",
            "created_at",
            "updated_at",
        )


class TeachingGroupSerializer(serializers.ModelSerializer):
    stream_name = serializers.CharField(
        source="stream.__str__",
        read_only=True,
    )

    class Meta:
        model = TeachingGroup
        fields = (
            "id",
            "stream",
            "stream_name",
            "name",
            "code",
            "learner_count",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "stream_name",
            "created_at",
            "updated_at",
        )


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = (
            "id",
            "name",
            "code",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class LessonRequirementSerializer(serializers.ModelSerializer):
    term_name = serializers.CharField(
        source="term.__str__",
        read_only=True,
    )

    teaching_group_name = serializers.CharField(
        source="instructional_group.__str__",
        read_only=True,
    )

    subject_name = serializers.CharField(
        source="subject.__str__",
        read_only=True,
    )

    class Meta:
        model = LessonRequirement
        fields = (
            "id",
            "term",
            "term_name",
            "instructional_group",
            "teaching_group_name",
            "subject",
            "subject_name",
            "lessons_per_week",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "term_name",
            "teaching_group_name",
            "subject_name",
            "created_at",
            "updated_at",
        )

    def validate_lessons_per_week(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Lessons per week must be at least 1."
            )

        return value
