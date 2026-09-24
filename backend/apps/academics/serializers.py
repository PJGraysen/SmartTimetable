from rest_framework import serializers



from rest_framework import serializers
from apps.academics.models import Student, StudentEnrollment


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    teaching_group_name = serializers.CharField(source="teaching_group.name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = StudentEnrollment
        fields = [
            "id", "student", "academic_year", "academic_year_name",
            "teaching_group", "teaching_group_name",
            "joined_on", "left_on", "is_current",
        ]


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    current_enrollment = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "admission_number",
            "first_name", "middle_name", "last_name", "full_name",
            "gender", "date_of_birth", "admission_date", "kcpe_mark",
            "status", "is_active",
            "current_enrollment",
            "created_at", "updated_at",
        ]

    def get_current_enrollment(self, obj):
        enrollment = (
            obj.enrollments.filter(is_current=True)
            .select_related("teaching_group")
            .first()
        )
        if not enrollment:
            return None
        return {
            "id": str(enrollment.id),
            "teaching_group_id": str(enrollment.teaching_group_id),
            "teaching_group_name": enrollment.teaching_group.name,
        }



from apps.academics.models import (
    Assessment, Result, GradingScheme, GradingBand,
    AcademicAuditEvent,
    ReportComment,
    RankingRule, RankingRun,
)


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = ["id", "name", "assessment_type", "date", "max_mark", "status"]


class ResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)

    class Meta:
        model = Result
        fields = ["id", "assessment", "student", "student_name",
                  "subject", "subject_code", "raw_mark", "status"]


class GradingBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingBand
        fields = ["id", "min_score", "max_score", "grade", "points", "descriptor"]


class GradingSchemeSerializer(serializers.ModelSerializer):
    bands = GradingBandSerializer(many=True, read_only=True)

    class Meta:
        model = GradingScheme
        fields = ["id", "name", "curriculum", "effective_from", "is_active", "bands"]



class RosterEntrySerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    admission_number = serializers.CharField()
    name = serializers.CharField()
    raw_mark = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)
    status = serializers.CharField()


class ResultBulkWriteSerializer(serializers.Serializer):
    assessment = serializers.UUIDField()
    subject = serializers.UUIDField()
    marks = serializers.ListField(child=serializers.DictField(), allow_empty=True)



class AcademicAuditEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, allow_null=True)
    actor_display = serializers.SerializerMethodField()

    class Meta:
        model = AcademicAuditEvent
        fields = [
            "id", "created_at", "actor", "actor_username", "actor_display",
            "action", "entity_type", "entity_id", "entity_label",
            "meta_json", "ip_address", "user_agent",
        ]

    def get_actor_display(self, obj):
        if not obj.actor:
            return None
        return getattr(obj.actor, "get_full_name", lambda: "")() or obj.actor.username



class ReportCommentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_admission = serializers.CharField(source="student.admission_number", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True)

    class Meta:
        model = ReportComment
        fields = [
            "id", "student", "student_name", "student_admission",
            "academic_year", "term", "term_name",
            "conduct", "class_teacher_comment",
            "rector_comment", "mission_comment",
            "created_at", "updated_at",
        ]



class RankingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RankingRule
        fields = [
            "id", "name", "description", "method", "tie_policy",
            "subject_codes", "min_subjects", "is_active", "version",
            "created_at", "updated_at",
        ]
        read_only_fields = ["version"]


class RankingRunSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)

    class Meta:
        model = RankingRun
        fields = [
            "id", "rule", "rule_name", "rule_snapshot", "assessment",
            "scope_type", "scope_id", "scope_label",
            "entries", "student_count", "notes",
            "created_at",
        ]
        read_only_fields = [
            "rule_snapshot", "entries", "student_count",
        ]
