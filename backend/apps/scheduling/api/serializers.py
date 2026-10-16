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
        fields = ("id",
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
            "updated_at", 'approved_at', 'approved_by', 'approval_note')

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

    scope_kind = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    scope_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    version_number = serializers.IntegerField(
        min_value=1,
        required=False,
        default=1,
    )
    baseline_version_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class TimetableEntryResultSerializer(serializers.ModelSerializer):
    """
    Detailed representation of one generated timetable entry.

    The API exposes both foreign-key IDs and human-readable fields for
    the frontend and other consumers.

    S1 addition: the ``block`` field exposes a synchronized-block display
    DTO. It is present only on entries whose subject belongs to a
    Grade 10 option block or a Senior School elective block. Otherwise it
    is null, and consumers should fall back to ``subject_code`` and
    ``teacher_code``.
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

    teacher_name = serializers.SerializerMethodField()

    teacher_code = serializers.CharField(
        source="teacher.employee_code",
        read_only=True,
        allow_null=True,
    )

    teacher_number = serializers.IntegerField(
        source="teacher.teacher_number",
        read_only=True,
        allow_null=True,
    )

    employee_code = serializers.CharField(
        source="teacher.employee_code",
        read_only=True,
        allow_null=True,
    )

    instructional_group_name = serializers.SerializerMethodField()
    instructional_group_code = serializers.SerializerMethodField()

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

    room_name = serializers.SerializerMethodField()
    learner_count = serializers.SerializerMethodField()

    room_code = serializers.CharField(
        source="room.code",
        read_only=True,
        allow_null=True,
    )

    # S1: synchronized-block display DTO
    block = serializers.SerializerMethodField()

    @staticmethod
    def get_teacher_name(entry):
        return str(entry.teacher) if entry.teacher is not None else None

    @staticmethod
    def get_instructional_group_name(entry):
        return (
            str(entry.instructional_group)
            if entry.instructional_group is not None
            else None
        )

    @staticmethod
    def get_instructional_group_code(entry):
        ig = getattr(entry, "instructional_group", None)
        if ig is None:
            return None
        code = getattr(ig, "code", None)
        return str(code).strip().upper() if code else None

    @staticmethod
    def get_room_name(entry):
        return str(entry.room) if entry.room is not None else None

    @staticmethod
    def get_learner_count(entry):
        ig = getattr(entry, "instructional_group", None)
        if ig is None:
            return None
        for attr in ("learner_count", "student_count", "enrolment_count", "enrollment_count", "learners"):
            v = getattr(ig, attr, None)
            if isinstance(v, int) and v > 0:
                return v
        tg = getattr(ig, "teaching_group", None)
        if tg is not None:
            for attr in ("learner_count", "student_count", "enrolment_count", "enrollment_count"):
                v = getattr(tg, attr, None)
                if isinstance(v, int) and v > 0:
                    return v
        try:
            n = ig.learners.count()
            if n > 0:
                return n
        except Exception:
            pass
        try:
            n = ig.students.count()
            if n > 0:
                return n
        except Exception:
            pass
        return None
        for attr in ("learner_count", "student_count", "learners", "capacity"):
            v = getattr(ig, attr, None)
            if isinstance(v, int) and v > 0:
                return v
        try:
            return ig.learners.count()
        except Exception:
            return None

    def get_block(self, entry):
        """
        Return the synchronized-block display DTO or None.

        Cached per (namespace, block_code, group_code) in self.context so
        the teacher map is resolved once per block/group rather than once
        per entry.
        """
        from apps.scheduling.engine.application.block_display import (
            build_display,
            resolve_block_membership,
        )

        cache = self.context.setdefault("_s1_block_cache", {})

        subject_code = None
        if entry.lesson_requirement is not None:
            subject = getattr(entry.lesson_requirement, "subject", None)
            if subject is not None:
                subject_code = getattr(subject, "code", None)

        membership = resolve_block_membership(
            subject_code=subject_code,
            group=entry.instructional_group,
        )
        if membership is None:
            return None

        namespace, block_code, subject_codes = membership
        group_code = str(
            getattr(entry.instructional_group, "code", "")
        ).strip().upper()
        cache_key = (namespace, block_code, group_code)

        if cache_key in cache:
            return cache[cache_key]

        teacher_map = self._resolve_member_teachers(
            entry=entry,
            subject_codes=subject_codes,
        )

        dto = build_display(
            namespace=namespace,
            block_code=block_code,
            subject_codes=subject_codes,
            teacher_map=teacher_map,
        )
        result = dto.to_dict()
        cache[cache_key] = result
        return result

    def _resolve_member_teachers(self, *, entry, subject_codes):
        """
        Map each block member subject_code -> teacher employee_code | None.

        Resolution order per member:
          1. TeacherAssignment for this entry's own instructional group
             and the same subject (active).
          2. If none, TeacherAssignment for the paired stream's group
             (10E<->10W, 3E<->3W, 4E<->4W) and the same subject.
          3. Otherwise None. Never manufactured.
        """
        from apps.scheduling.models import TeacherAssignment

        term = entry.timetable_version.term
        group = entry.instructional_group
        group_code = str(getattr(group, "code", "")).strip().upper()

        pair_map = {
            "10E": "10W",
            "10W": "10E",
            "3E": "3W",
            "3W": "3E",
            "4E": "4W",
            "4W": "4E",
        }
        paired_code = pair_map.get(group_code)

        normalized = [str(sc).strip().upper() for sc in subject_codes]
        teacher_map: dict[str, str | None] = {sc: None for sc in normalized}

        own_qs = (
            TeacherAssignment.objects
            .filter(
                is_active=True,
                lesson_requirement__is_active=True,
                lesson_requirement__term=term,
                lesson_requirement__instructional_group=group,
                lesson_requirement__subject__code__in=normalized,
            )
            .select_related("teacher", "lesson_requirement__subject")
        )
        for ta in own_qs:
            subj = ta.lesson_requirement.subject.code.strip().upper()
            if ta.teacher is not None and ta.teacher.employee_code:
                if teacher_map.get(subj) is None:
                    teacher_map[subj] = ta.teacher.employee_code

        missing = [sc for sc in normalized if teacher_map.get(sc) is None]
        if paired_code and missing:
            pair_qs = (
                TeacherAssignment.objects
                .filter(
                    is_active=True,
                    lesson_requirement__is_active=True,
                    lesson_requirement__term=term,
                    lesson_requirement__instructional_group__code=paired_code,
                    lesson_requirement__subject__code__in=missing,
                )
                .select_related("teacher", "lesson_requirement__subject")
            )
            for ta in pair_qs:
                subj = ta.lesson_requirement.subject.code.strip().upper()
                if teacher_map.get(subj) is None:
                    if ta.teacher is not None and ta.teacher.employee_code:
                        teacher_map[subj] = ta.teacher.employee_code

        return teacher_map

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
            "instructional_group_code",
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
            "room_code",
            "learner_count",
            "block",
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

class SchedulingRuleConfigSerializer(serializers.ModelSerializer):
    """Rule toggles for one term."""

    term_name = serializers.CharField(source="term.__str__", read_only=True)

    class Meta:
        from apps.scheduling.models import SchedulingRuleConfig as _C
        model = _C
        fields = (
            "id",
            "term",
            "term_name",
            "cross_stream_practicals_enabled",
            "block_sync_enabled",
            "teacher_max_consecutive_enabled",
            "complex_adjacency_enabled",
            "eng_grade10_sync_enabled",
            "single_lesson_per_day_enabled",
            "teacher_free_afternoon_enabled",
            "practical_double_lesson_enabled",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "term", "term_name", "created_at", "updated_at")

