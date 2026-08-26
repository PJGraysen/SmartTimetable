from django.contrib.auth.models import User
from rest_framework import serializers

from apps.academics.models import Grade, Stream, Subject, TeachingGroup
from apps.core.models import AcademicYear, School
from apps.scheduling.models import Room
from apps.users.models import Teacher


class ManagementTeachingGroupSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(write_only=True)
    grade_code = serializers.CharField(write_only=True)
    stream_name = serializers.CharField(write_only=True)
    stream_code = serializers.CharField(write_only=True)

    grade = serializers.CharField(source="stream.grade.name", read_only=True)
    stream = serializers.CharField(source="stream.name", read_only=True)

    class Meta:
        model = TeachingGroup
        fields = [
            "id",
            "code",
            "name",
            "learner_count",
            "is_active",
            "grade_name",
            "grade_code",
            "stream_name",
            "stream_code",
            "grade",
            "stream",
        ]

    def _get_academic_year(self):
        school = (
            School.objects
            .filter(is_active=True)
            .order_by("name")
            .first()
        )

        if school is None:
            school = School.objects.create(
                name="Queen of Apostles Seminary",
                code="QASS",
                is_active=True,
            )

        year = (
            school.academic_years
            .filter(is_active=True)
            .order_by("-start_date")
            .first()
        )

        if year is None:
            raise serializers.ValidationError(
                "No active academic year exists."
            )

        return year

    def create(self, validated_data):
        grade_name = validated_data.pop("grade_name")
        grade_code = validated_data.pop("grade_code")
        stream_name = validated_data.pop("stream_name")
        stream_code = validated_data.pop("stream_code")

        academic_year = self._get_academic_year()

        grade, _ = Grade.objects.get_or_create(
            academic_year=academic_year,
            code=grade_code,
            defaults={
                "name": grade_name,
            },
        )

        changed = False

        if grade.name != grade_name:
            grade.name = grade_name
            grade.save(update_fields=["name", "updated_at"])
            changed = True

        stream, _ = Stream.objects.get_or_create(
            grade=grade,
            code=stream_code,
            defaults={
                "name": stream_name,
            },
        )

        if stream.name != stream_name:
            stream.name = stream_name
            stream.save(update_fields=["name", "updated_at"])

        return TeachingGroup.objects.create(
            stream=stream,
            **validated_data,
        )

    def update(self, instance, validated_data):
        grade_name = validated_data.pop("grade_name", None)
        grade_code = validated_data.pop("grade_code", None)
        stream_name = validated_data.pop("stream_name", None)
        stream_code = validated_data.pop("stream_code", None)

        if any(
            value is not None
            for value in (
                grade_name,
                grade_code,
                stream_name,
                stream_code,
            )
        ):
            academic_year = self._get_academic_year()

            grade = instance.stream.grade

            if grade_code is not None and grade.code != grade_code:
                grade.code = grade_code

            if grade_name is not None and grade.name != grade_name:
                grade.name = grade_name

            grade.save()

            stream = instance.stream

            if stream_code is not None:
                stream.code = stream_code

            if stream_name is not None:
                stream.name = stream_name

            stream.save()

        return super().update(instance, validated_data)


class ManagementTeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = [
            "id",
            "employee_code",
            "first_name",
            "last_name",
            "is_active",
        ]

    def create(self, validated_data):
        employee_code = validated_data["employee_code"]

        username = f"teacher_{employee_code.lower()}"

        user = User.objects.filter(username=username).first()

        if user is None:
            user = User.objects.create(
                username=username,
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
            )
            user.set_unusable_password()
            user.save()

        return Teacher.objects.create(
            user=user,
            **validated_data,
        )

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        instance.user.first_name = instance.first_name
        instance.user.last_name = instance.last_name
        instance.user.save(
            update_fields=["first_name", "last_name"]
        )

        return instance


class ManagementSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = [
            "id",
            "code",
            "name",
            "is_active",
        ]


class ManagementRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            "id",
            "code",
            "name",
            "capacity",
            "is_active",
        ]

    def _get_school(self):
        school = (
            School.objects
            .filter(is_active=True)
            .order_by("name")
            .first()
        )

        if school is None:
            school = School.objects.create(
                name="Queen of Apostles Seminary",
                code="QASS",
                is_active=True,
            )

        return school

    def create(self, validated_data):
        return Room.objects.create(
            school=self._get_school(),
            **validated_data,
        )