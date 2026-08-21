from __future__ import annotations

from rest_framework import serializers

from apps.core.models import (
    AcademicYear,
    School,
    Term,
)


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
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


class AcademicYearSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(
        source="school.name",
        read_only=True,
    )

    class Meta:
        model = AcademicYear
        fields = (
            "id",
            "school",
            "school_name",
            "name",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "school_name",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                "End date must be on or after start date."
            )

        return attrs


class TermSerializer(serializers.ModelSerializer):
    """
    Serializer for academic terms used by the frontend and API clients.
    """

    academic_year_name = serializers.CharField(
        source="academic_year.name",
        read_only=True,
    )

    class Meta:
        model = Term
        fields = (
            "id",
            "academic_year",
            "academic_year_name",
            "name",
            "number",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "academic_year_name",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                "End date must be on or after start date."
            )

        return attrs

    def validate_number(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Term number must be at least 1."
            )

        return value
