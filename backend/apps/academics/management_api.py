from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.academics.models import Grade, Stream, TeachingGroup, Subject
from apps.users.models import Teacher
from apps.scheduling.models import Room


def _json(request):
    import json

    if not request.body:
        return {}

    return json.loads(
        request.body.decode("utf-8")
    )


def _error(message, status=400):
    return JsonResponse(
        {
            "detail": str(message),
            "error": str(message),
        },
        status=status,
    )


def _ok(data=None, status=200):
    payload = {
        "success": True,
    }

    if data:
        payload.update(data)

    return JsonResponse(payload, status=status)


def _bool(value, default=True):
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _int(value, default=0):
    if value in (None, ""):
        return default

    return int(value)


def _group_dict(group):
    return {
        "id": str(group.pk),
        "code": group.code,
        "name": group.name,
        "learner_count": group.learner_count,
        "is_active": bool(group.is_active),
        "grade": (
            group.stream.grade.name
            if group.stream and group.stream.grade
            else None
        ),
        "grade_code": (
            group.stream.grade.code
            if group.stream and group.stream.grade
            else None
        ),
        "stream": (
            group.stream.name
            if group.stream
            else None
        ),
        "stream_code": (
            group.stream.code
            if group.stream
            else None
        ),
    }


def _teacher_dict(teacher):
    return {
        "id": str(teacher.pk),
        "employee_code": teacher.employee_code,
        "first_name": teacher.first_name,
        "last_name": teacher.last_name,
        "is_active": bool(teacher.is_active),
    }


def _subject_dict(subject):
    return {
        "id": str(subject.pk),
        "code": subject.code,
        "name": subject.name,
        "is_active": bool(subject.is_active),
    }


def _room_dict(room):
    return {
        "id": str(room.pk),
        "code": room.code,
        "name": room.name,
        "capacity": room.capacity,
        "is_active": bool(room.is_active),
    }


def _active_school():
    return (
        __import__(
            "apps.core.models",
            fromlist=["School"],
        )
        .School.objects
        .filter(is_active=True)
        .order_by("name")
        .first()
    )


def _active_academic_year(school):
    if school is None:
        return None

    return (
        school.academic_years
        .filter(is_active=True)
        .order_by("-start_date")
        .first()
    )


@require_http_methods(["GET"])
def summary(request):
    return _ok(
        {
            "counts": {
                "teaching_groups":
                    TeachingGroup.objects.count(),

                "teachers":
                    Teacher.objects.count(),

                "subjects":
                    Subject.objects.count(),

                "rooms":
                    Room.objects.count(),
            }
        }
    )


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE"])
def teaching_groups(request):

    if request.method == "GET":

        groups = (
            TeachingGroup.objects
            .select_related(
                "stream",
                "stream__grade",
            )
            .order_by(
                "stream__grade__code",
                "stream__code",
                "code",
            )
        )

        return JsonResponse(
            [_group_dict(group) for group in groups],
            safe=False,
        )

    try:
        payload = _json(request)

        if request.method == "POST":

            grade_name = (
                payload.get("grade_name")
                or payload.get("grade")
            )

            grade_code = (
                payload.get("grade_code")
                or payload.get("gradeCode")
            )

            stream_name = (
                payload.get("stream_name")
                or payload.get("stream")
            )

            stream_code = (
                payload.get("stream_code")
                or payload.get("streamCode")
            )

            group_name = payload.get("name")
            group_code = payload.get("code")

            if not all(
                [
                    grade_name,
                    grade_code,
                    stream_name,
                    stream_code,
                    group_name,
                    group_code,
                ]
            ):
                return _error(
                    "Grade, grade code, stream, stream code, "
                    "group name and group code are required."
                )

            school = _active_school()

            if school is None:
                return _error(
                    "No active school exists.",
                    409,
                )

            academic_year = _active_academic_year(school)

            if academic_year is None:
                return _error(
                    "No active academic year exists.",
                    409,
                )

            with transaction.atomic():

                grade = (
                    Grade.objects
                    .filter(
                        academic_year=academic_year,
                        code=grade_code,
                    )
                    .first()
                )

                if grade is None:

                    grade_by_name = (
                        Grade.objects
                        .filter(
                            academic_year=academic_year,
                            name=grade_name,
                        )
                        .first()
                    )

                    if grade_by_name:
                        grade = grade_by_name

                    else:
                        grade = Grade.objects.create(
                            academic_year=academic_year,
                            name=grade_name,
                            code=grade_code,
                        )

                stream = (
                    Stream.objects
                    .filter(
                        grade=grade,
                        code=stream_code,
                    )
                    .first()
                )

                if stream is None:

                    stream_by_name = (
                        Stream.objects
                        .filter(
                            grade=grade,
                            name=stream_name,
                        )
                        .first()
                    )

                    if stream_by_name:
                        stream = stream_by_name

                    else:
                        stream = Stream.objects.create(
                            grade=grade,
                            name=stream_name,
                            code=stream_code,
                        )

                group = (
                    TeachingGroup.objects
                    .filter(code=group_code)
                    .first()
                )

                if group is None:

                    group = TeachingGroup.objects.create(
                        stream=stream,
                        name=group_name,
                        code=group_code,
                        learner_count=_int(
                            payload.get(
                                "learner_count"
                            ),
                            45,
                        ),
                        is_active=_bool(
                            payload.get("is_active"),
                            True,
                        ),
                    )

                else:

                    group.stream = stream
                    group.name = group_name

                    if "learner_count" in payload:
                        group.learner_count = _int(
                            payload.get(
                                "learner_count"
                            ),
                            group.learner_count,
                        )

                    if "is_active" in payload:
                        group.is_active = _bool(
                            payload.get("is_active")
                        )

                    group.save()

                return _ok(
                    {
                        "item": _group_dict(group),
                    },
                    201,
                )

        if request.method in {"PUT", "PATCH"}:

            object_id = payload.get("id")

            if not object_id:
                return _error(
                    "Teaching group id is required."
                )

            group = (
                TeachingGroup.objects
                .select_related(
                    "stream",
                    "stream__grade",
                )
                .filter(pk=object_id)
                .first()
            )

            if group is None:
                return _error(
                    "Teaching group not found.",
                    404,
                )

            if "name" in payload:
                group.name = payload["name"]

            if "learner_count" in payload:
                group.learner_count = _int(
                    payload["learner_count"],
                    group.learner_count,
                )

            if "is_active" in payload:
                group.is_active = _bool(
                    payload["is_active"]
                )

            group.save()

            return _ok(
                {
                    "item": _group_dict(group),
                }
            )

        if request.method == "DELETE":

            object_id = payload.get("id")

            if not object_id:
                return _error(
                    "Teaching group id is required."
                )

            group = (
                TeachingGroup.objects
                .filter(pk=object_id)
                .first()
            )

            if group is None:
                return _error(
                    "Teaching group not found.",
                    404,
                )

            group.is_active = False
            group.save(
                update_fields=["is_active"]
            )

            return _ok()

    except Exception as exc:
        return _error(str(exc), 400)


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE"])
def teachers(request):

    if request.method == "GET":

        teachers = (
            Teacher.objects
            .order_by("employee_code")
        )

        return JsonResponse(
            [
                _teacher_dict(teacher)
                for teacher in teachers
            ],
            safe=False,
        )

    try:

        payload = _json(request)

        if request.method == "POST":

            code = (
                payload.get("employee_code")
                or payload.get("code")
            )

            if not code:
                return _error(
                    "Employee code is required."
                )

            teacher = (
                Teacher.objects
                .filter(employee_code=code)
                .first()
            )

            if teacher is not None:

                return _error(
                    "A teacher with this employee code "
                    "already exists.",
                    409,
                )

            first_name = payload.get(
                "first_name",
                "",
            )

            last_name = payload.get(
                "last_name",
                "",
            )

            username = (
                f"teacher_{code.lower()}"
            )

            user = (
                User.objects
                .filter(username=username)
                .first()
            )

            if user is None:

                user = User.objects.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                )

                user.set_unusable_password()
                user.save()

            teacher = Teacher.objects.create(
                user=user,
                employee_code=code,
                first_name=first_name,
                last_name=last_name,
                is_active=_bool(
                    payload.get("is_active"),
                    True,
                ),
            )

            return _ok(
                {
                    "item": _teacher_dict(
                        teacher
                    ),
                },
                201,
            )

        if request.method in {"PUT", "PATCH"}:

            object_id = payload.get("id")

            teacher = (
                Teacher.objects
                .filter(pk=object_id)
                .first()
            )

            if teacher is None:
                return _error(
                    "Teacher not found.",
                    404,
                )

            if "first_name" in payload:
                teacher.first_name = (
                    payload["first_name"]
                )

            if "last_name" in payload:
                teacher.last_name = (
                    payload["last_name"]
                )

            if "is_active" in payload:
                teacher.is_active = _bool(
                    payload["is_active"]
                )

            teacher.save()

            if teacher.user_id:

                user = teacher.user

                user.first_name = (
                    teacher.first_name
                )

                user.last_name = (
                    teacher.last_name
                )

                user.save(
                    update_fields=[
                        "first_name",
                        "last_name",
                    ]
                )

            return _ok(
                {
                    "item": _teacher_dict(
                        teacher
                    ),
                }
            )

        if request.method == "DELETE":

            object_id = payload.get("id")

            teacher = (
                Teacher.objects
                .filter(pk=object_id)
                .first()
            )

            if teacher is None:
                return _error(
                    "Teacher not found.",
                    404,
                )

            teacher.is_active = False
            teacher.save(
                update_fields=["is_active"]
            )

            return _ok()

    except Exception as exc:
        return _error(str(exc), 400)


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE"])
def subjects(request):

    if request.method == "GET":

        subjects = (
            Subject.objects
            .order_by("code")
        )

        return JsonResponse(
            [
                _subject_dict(subject)
                for subject in subjects
            ],
            safe=False,
        )

    try:

        payload = _json(request)

        if request.method == "POST":

            code = payload.get("code")
            name = payload.get("name")

            if not code or not name:
                return _error(
                    "Subject code and name are required."
                )

            by_code = (
                Subject.objects
                .filter(code=code)
                .first()
            )

            by_name = (
                Subject.objects
                .filter(name=name)
                .first()
            )

            if by_code and by_name:
                if by_code.pk != by_name.pk:
                    return _error(
                        "Subject code and subject name "
                        "belong to different existing records. "
                        "No duplicate was created.",
                        409,
                    )

                subject = by_code

            elif by_code:
                subject = by_code

            elif by_name:
                subject = by_name

            else:
                subject = Subject.objects.create(
                    code=code,
                    name=name,
                    is_active=_bool(
                        payload.get("is_active"),
                        True,
                    ),
                )

            changed = False

            if subject.code != code:
                subject.code = code
                changed = True

            if subject.name != name:
                subject.name = name
                changed = True

            if "is_active" in payload:
                subject.is_active = _bool(
                    payload["is_active"]
                )
                changed = True

            if changed:
                subject.save()

            return _ok(
                {
                    "item": _subject_dict(
                        subject
                    ),
                },
                201,
            )

        if request.method in {"PUT", "PATCH"}:

            object_id = payload.get("id")

            subject = (
                Subject.objects
                .filter(pk=object_id)
                .first()
            )

            if subject is None:
                return _error(
                    "Subject not found.",
                    404,
                )

            if "code" in payload:

                duplicate_code = (
                    Subject.objects
                    .filter(
                        code=payload["code"]
                    )
                    .exclude(pk=subject.pk)
                    .first()
                )

                if duplicate_code:
                    return _error(
                        "Another subject already uses "
                        "that code.",
                        409,
                    )

                subject.code = payload["code"]

            if "name" in payload:

                duplicate_name = (
                    Subject.objects
                    .filter(
                        name=payload["name"]
                    )
                    .exclude(pk=subject.pk)
                    .first()
                )

                if duplicate_name:
                    return _error(
                        "Another subject already uses "
                        "that name.",
                        409,
                    )

                subject.name = payload["name"]

            if "is_active" in payload:
                subject.is_active = _bool(
                    payload["is_active"]
                )

            subject.save()

            return _ok(
                {
                    "item": _subject_dict(
                        subject
                    ),
                }
            )

        if request.method == "DELETE":

            object_id = payload.get("id")

            subject = (
                Subject.objects
                .filter(pk=object_id)
                .first()
            )

            if subject is None:
                return _error(
                    "Subject not found.",
                    404,
                )

            subject.is_active = False
            subject.save(
                update_fields=["is_active"]
            )

            return _ok()

    except Exception as exc:
        return _error(str(exc), 400)


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE"])
def rooms(request):

    if request.method == "GET":

        rooms = (
            Room.objects
            .order_by("code")
        )

        return JsonResponse(
            [
                _room_dict(room)
                for room in rooms
            ],
            safe=False,
        )

    try:

        payload = _json(request)

        school = _active_school()

        if school is None:
            return _error(
                "No active school exists.",
                409,
            )

        if request.method == "POST":

            code = payload.get("code")
            name = payload.get("name")

            if not code or not name:
                return _error(
                    "Room code and name are required."
                )

            room = (
                Room.objects
                .filter(
                    school=school,
                    code=code,
                )
                .first()
            )

            if room is None:

                room = Room.objects.create(
                    school=school,
                    code=code,
                    name=name,
                    capacity=_int(
                        payload.get("capacity"),
                        45,
                    ),
                    is_active=_bool(
                        payload.get("is_active"),
                        True,
                    ),
                )

            else:

                room.name = name
                room.capacity = _int(
                    payload.get("capacity"),
                    room.capacity,
                )

                if "is_active" in payload:
                    room.is_active = _bool(
                        payload["is_active"]
                    )

                room.save()

            return _ok(
                {
                    "item": _room_dict(room),
                },
                201,
            )

        if request.method in {"PUT", "PATCH"}:

            room = (
                Room.objects
                .filter(pk=payload.get("id"))
                .first()
            )

            if room is None:
                return _error(
                    "Room not found.",
                    404,
                )

            if "code" in payload:

                duplicate = (
                    Room.objects
                    .filter(
                        school=school,
                        code=payload["code"],
                    )
                    .exclude(pk=room.pk)
                    .first()
                )

                if duplicate:
                    return _error(
                        "Another room already uses "
                        "that code.",
                        409,
                    )

                room.code = payload["code"]

            if "name" in payload:
                room.name = payload["name"]

            if "capacity" in payload:
                room.capacity = _int(
                    payload["capacity"],
                    room.capacity,
                )

            if "is_active" in payload:
                room.is_active = _bool(
                    payload["is_active"]
                )

            room.save()

            return _ok(
                {
                    "item": _room_dict(room),
                }
            )

        if request.method == "DELETE":

            room = (
                Room.objects
                .filter(pk=payload.get("id"))
                .first()
            )

            if room is None:
                return _error(
                    "Room not found.",
                    404,
                )

            room.is_active = False
            room.save(
                update_fields=["is_active"]
            )

            return _ok()

    except Exception as exc:
        return _error(str(exc), 400)