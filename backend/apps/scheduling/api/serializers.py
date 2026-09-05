from __future__ import annotations

from rest_framework import serializers

from apps.scheduling.models import (
    Period,
    SchedulingRun,
    TimetableEntry,
    TimetableVersion,
)


class SchedulingRunCreateSerializer(serializers.ModelSerializer):
    """
    Serializer used to create a new scheduling run.
    """

    class Meta:
        model = SchedulingRun
        fields = ("term",)


class SchedulingRunSerializer(serializers.ModelSerializer):
    """
    Standard scheduling-run serializer.

    Used for listing and retrieving scheduling runs.
    """

    term_name = serializers.CharField(
        source="term.name",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    solver_status_display = serializers.CharField(
        source="get_solver_status_display",
        read_only=True,
    )

    class Meta:
        model = SchedulingRun
        fields = (
            "id",
            "term",
            "term_name",
            "timetable_version",
            "status",
            "status_display",
            "solver_status",
            "solver_status_display",
            "started_at",
            "completed_at",
            "objective_value",
            "error_message",
            "statistics",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "timetable_version",
            "status",
            "status_display",
            "solver_status",
            "solver_status_display",
            "started_at",
            "completed_at",
            "objective_value",
            "error_message",
            "statistics",
            "created_at",
            "updated_at",
        )


class SchedulingRunExecuteSerializer(serializers.Serializer):
    """
    Serializer for timetable-generation execution parameters.
    """

    version_name = serializers.CharField(
        max_length=255,
        required=False,
        default="Generated Timetable",
    )

    version_number = serializers.IntegerField(
        min_value=1,
        required=False,
        default=1,
    )


class TimetableEntryResultSerializer(serializers.ModelSerializer):
    """
    Detailed representation of one generated timetable entry.

    The API exposes both the foreign-key IDs and useful human-readable
    information for the frontend and other API consumers.
    """

    day_display = serializers.CharField(
        source="get_day_display",
        read_only=True,
    )

    period_number = serializers.IntegerField(
        source="period.number",
        read_only=True,
    )

    period_name = serializers.CharField(
        source="period.name",
        read_only=True,
    )

    period_start_time = serializers.TimeField(
        source="period.start_time",
        read_only=True,
    )

    period_end_time = serializers.TimeField(
        source="period.end_time",
        read_only=True,
    )

    teacher_name = serializers.CharField(
        source="teacher.__str__",
        read_only=True,
    )

    teacher_code = serializers.CharField(
        source="teacher.employee_code",
        read_only=True,
    )

    teacher_number = serializers.IntegerField(
        source="teacher.teacher_number",
        read_only=True,
        allow_null=True,
    )

    employee_code = serializers.CharField(
        source="teacher.employee_code",
        read_only=True,
    )

    instructional_group_name = serializers.CharField(
        source="instructional_group.__str__",
        read_only=True,
    )

    lesson_requirement_name = serializers.CharField(
        source="lesson_requirement.__str__",
        read_only=True,
    )

    subject_name = serializers.CharField(
        source="lesson_requirement.subject.name",
        read_only=True,
    )

    subject_code = serializers.CharField(
        source="lesson_requirement.subject.code",
        read_only=True,
    )

    room_name = serializers.CharField(
        source="room.__str__",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = TimetableEntry
        fields = (
            "id",
            "day",
            "day_display",
            "period",
            "period_number",
            "period_name",
            "period_start_time",
            "period_end_time",
            "instructional_group",
            "instructional_group_name",
            "teacher",
            "teacher_name",
            "teacher_code",
            "teacher_number",
            "employee_code",
            "lesson_requirement",
            "lesson_requirement_name",
            "subject_name",
            "subject_code",
            "room",
            "room_name",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields


class TimetableVersionResultSerializer(serializers.ModelSerializer):
    """
    Detailed representation of a generated timetable version.
    """

    term_name = serializers.CharField(
        source="term.name",
        read_only=True,
    )

    entries = TimetableEntryResultSerializer(
        many=True,
        read_only=True,
    )

    entries_count = serializers.IntegerField(
        source="entries.count",
        read_only=True,
    )

    slots = serializers.SerializerMethodField()

    @staticmethod
    def get_slots(_version):
        """Expose the backend's authoritative 49 lesson slots to the UI."""
        from apps.scheduling.engine.infrastructure.django_loader import (
            build_timetable_slots,
            load_periods,
        )

        periods = Period.objects.filter(is_active=True).order_by("number", "id")
        period_by_id = {period.id: period for period in periods}

        return [
            {
                "day": slot.day.value,
                "period": str(slot.period_id),
                "period_number": slot.period_number,
                "period_name": period_by_id[slot.period_id].name,
                "period_start_time": period_by_id[slot.period_id].start_time,
                "period_end_time": period_by_id[slot.period_id].end_time,
            }
            for slot in build_timetable_slots(load_periods(periods))
        ]

    class Meta:
        model = TimetableVersion
        fields = (
            "id",
            "term",
            "term_name",
            "name",
            "version_number",
            "is_published",
            "is_active",
            "entries_count",
            "entries",
            "slots",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields


class SchedulingRunResultSerializer(serializers.ModelSerializer):
    """
    Detailed result serializer for a scheduling run.

    Unlike the standard SchedulingRunSerializer, this serializer
    expands the generated timetable version and its timetable entries.
    """

    timetable_version = TimetableVersionResultSerializer(
        read_only=True,
    )

    class Meta:
        model = SchedulingRun
        fields = (
            "id",
            "term",
            "timetable_version",
            "status",
            "solver_status",
            "started_at",
            "completed_at",
            "objective_value",
            "error_message",
            "statistics",
        )

        read_only_fields = fields

