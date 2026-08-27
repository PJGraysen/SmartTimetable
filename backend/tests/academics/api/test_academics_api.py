from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import (
    Grade,
    LessonRequirement,
    Stream,
    Subject,
    TeachingGroup,
)


@pytest.fixture
def api_client():
    return APIClient()


# ---------------------------------------------------------------------------
# Instructional group API
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_instructional_groups(api_client, instructional_group):
    response = api_client.get("/api/academics/instructional-groups/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1

    result = response.data[0]
    assert result["id"] == str(instructional_group.id)
    assert result["name"] == instructional_group.name
    assert str(result["teaching_group"]) == str(
        instructional_group.teaching_group_id
    )
    assert result["teaching_group_name"] == str(
        instructional_group.teaching_group
    )

    create_response = api_client.post(
        "/api/academics/instructional-groups/",
        {},
        format="json",
    )
    assert create_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ---------------------------------------------------------------------------
# Grade API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_grades(api_client, grade):
    response = api_client.get("/api/academics/grades/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == str(grade.id)
    assert response.data[0]["name"] == grade.name
    assert response.data[0]["code"] == grade.code


@pytest.mark.django_db
def test_create_grade(api_client, academic_year):
    response = api_client.post(
        "/api/academics/grades/",
        {
            "academic_year": str(academic_year.id),
            "name": "Grade 11",
            "code": "G11",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    grade = Grade.objects.get(id=response.data["id"])

    assert grade.academic_year_id == academic_year.id
    assert grade.name == "Grade 11"
    assert grade.code == "G11"


@pytest.mark.django_db
def test_retrieve_grade(api_client, grade):
    response = api_client.get(
        f"/api/academics/grades/{grade.id}/",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(grade.id)
    assert response.data["name"] == grade.name


@pytest.mark.django_db
def test_update_grade(api_client, grade):
    response = api_client.patch(
        f"/api/academics/grades/{grade.id}/",
        {"name": "Updated Grade"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    grade.refresh_from_db()

    assert grade.name == "Updated Grade"


@pytest.mark.django_db
def test_delete_grade(api_client, grade):
    grade_id = grade.id

    response = api_client.delete(
        f"/api/academics/grades/{grade_id}/",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Grade.objects.filter(id=grade_id).exists()


# ---------------------------------------------------------------------------
# Stream API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_streams(api_client, stream):
    response = api_client.get("/api/academics/streams/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == str(stream.id)
    assert response.data[0]["name"] == stream.name


@pytest.mark.django_db
def test_create_stream(api_client, grade):
    response = api_client.post(
        "/api/academics/streams/",
        {
            "grade": str(grade.id),
            "name": "Stream B",
            "code": "B",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    stream = Stream.objects.get(id=response.data["id"])

    assert stream.grade_id == grade.id
    assert stream.name == "Stream B"
    assert stream.code == "B"


@pytest.mark.django_db
def test_retrieve_stream(api_client, stream):
    response = api_client.get(
        f"/api/academics/streams/{stream.id}/",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(stream.id)


@pytest.mark.django_db
def test_update_stream(api_client, stream):
    response = api_client.patch(
        f"/api/academics/streams/{stream.id}/",
        {"name": "Updated Stream"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    stream.refresh_from_db()

    assert stream.name == "Updated Stream"


@pytest.mark.django_db
def test_delete_stream(api_client, stream):
    stream_id = stream.id

    response = api_client.delete(
        f"/api/academics/streams/{stream_id}/",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Stream.objects.filter(id=stream_id).exists()


# ---------------------------------------------------------------------------
# Teaching Group API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_teaching_groups(api_client, teaching_group):
    response = api_client.get(
        "/api/academics/teaching-groups/",
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == str(teaching_group.id)
    assert response.data[0]["name"] == teaching_group.name


@pytest.mark.django_db
def test_create_teaching_group(api_client, stream):
    response = api_client.post(
        "/api/academics/teaching-groups/",
        {
            "stream": str(stream.id),
            "name": "Group B",
            "code": "GB",
            "learner_count": 35,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    group = TeachingGroup.objects.get(id=response.data["id"])

    assert group.stream_id == stream.id
    assert group.name == "Group B"
    assert group.code == "GB"
    assert group.learner_count == 35


@pytest.mark.django_db
def test_retrieve_teaching_group(api_client, teaching_group):
    response = api_client.get(
        f"/api/academics/teaching-groups/{teaching_group.id}/",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(teaching_group.id)


@pytest.mark.django_db
def test_update_teaching_group(api_client, teaching_group):
    response = api_client.patch(
        f"/api/academics/teaching-groups/{teaching_group.id}/",
        {
            "learner_count": 40,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    teaching_group.refresh_from_db()

    assert teaching_group.learner_count == 40


@pytest.mark.django_db
def test_delete_teaching_group(api_client, teaching_group):
    group_id = teaching_group.id

    response = api_client.delete(
        f"/api/academics/teaching-groups/{group_id}/",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not TeachingGroup.objects.filter(id=group_id).exists()


# ---------------------------------------------------------------------------
# Subject API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_subjects(api_client, subject):
    response = api_client.get("/api/academics/subjects/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == str(subject.id)
    assert response.data[0]["name"] == subject.name
    assert response.data[0]["code"] == subject.code


@pytest.mark.django_db
def test_create_subject(api_client):
    response = api_client.post(
        "/api/academics/subjects/",
        {
            "name": "Physics",
            "code": "PHY",
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    subject = Subject.objects.get(id=response.data["id"])

    assert subject.name == "Physics"
    assert subject.code == "PHY"
    assert subject.is_active is True


@pytest.mark.django_db
def test_retrieve_subject(api_client, subject):
    response = api_client.get(
        f"/api/academics/subjects/{subject.id}/",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(subject.id)


@pytest.mark.django_db
def test_update_subject(api_client, subject):
    response = api_client.patch(
        f"/api/academics/subjects/{subject.id}/",
        {"name": "Updated Subject"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    subject.refresh_from_db()

    assert subject.name == "Updated Subject"


@pytest.mark.django_db
def test_delete_subject(api_client, subject):
    subject_id = subject.id

    response = api_client.delete(
        f"/api/academics/subjects/{subject_id}/",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Subject.objects.filter(id=subject_id).exists()


# ---------------------------------------------------------------------------
# Lesson Requirement API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_lesson_requirements(api_client, lesson_requirement):
    response = api_client.get(
        "/api/academics/lesson-requirements/",
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == str(lesson_requirement.id)
    assert (
        response.data[0]["lessons_per_week"]
        == lesson_requirement.lessons_per_week
    )


@pytest.mark.django_db
def test_create_lesson_requirement(
    api_client,
    term,
    instructional_group,
    subject,
):
    response = api_client.post(
        "/api/academics/lesson-requirements/",
        {
            "term": str(term.id),
            "instructional_group": str(instructional_group.id),
            "subject": str(subject.id),
            "lessons_per_week": 4,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    requirement = LessonRequirement.objects.get(
        id=response.data["id"],
    )

    assert requirement.term_id == term.id
    assert requirement.instructional_group_id == instructional_group.id
    assert requirement.subject_id == subject.id
    assert requirement.lessons_per_week == 4


@pytest.mark.django_db
def test_retrieve_lesson_requirement(
    api_client,
    lesson_requirement,
):
    response = api_client.get(
        "/api/academics/lesson-requirements/"
        f"{lesson_requirement.id}/",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(lesson_requirement.id)


@pytest.mark.django_db
def test_update_lesson_requirement(
    api_client,
    lesson_requirement,
):
    response = api_client.patch(
        "/api/academics/lesson-requirements/"
        f"{lesson_requirement.id}/",
        {
            "lessons_per_week": 5,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    lesson_requirement.refresh_from_db()

    assert lesson_requirement.lessons_per_week == 5


@pytest.mark.django_db
def test_delete_lesson_requirement(
    api_client,
    lesson_requirement,
):
    requirement_id = lesson_requirement.id

    response = api_client.delete(
        "/api/academics/lesson-requirements/"
        f"{requirement_id}/",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not LessonRequirement.objects.filter(
        id=requirement_id,
    ).exists()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_grade_rejects_duplicate_name(
    api_client,
    grade,
):
    response = api_client.post(
        "/api/academics/grades/",
        {
            "academic_year": str(grade.academic_year_id),
            "name": grade.name,
            "code": "DIFFERENT",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_subject_rejects_duplicate_code(
    api_client,
    subject,
):
    response = api_client.post(
        "/api/academics/subjects/",
        {
            "name": "Different Subject",
            "code": subject.code,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_lesson_requirement_rejects_duplicate(
    api_client,
    lesson_requirement,
):
    response = api_client.post(
        "/api/academics/lesson-requirements/",
        {
            "term": str(lesson_requirement.term_id),
            "instructional_group": str(
                lesson_requirement.instructional_group_id,
            ),
            "subject": str(lesson_requirement.subject_id),
            "lessons_per_week": 4,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_lesson_requirement_rejects_zero_lessons(
    api_client,
    term,
    instructional_group,
    subject,
):
    response = api_client.post(
        "/api/academics/lesson-requirements/",
        {
            "term": str(term.id),
            "instructional_group": str(instructional_group.id),
            "subject": str(subject.id),
            "lessons_per_week": 0,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
