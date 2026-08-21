import pytest
from rest_framework.test import APIClient

from apps.core.models import (
    AcademicYear,
    School,
    Term,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def school():
    return School.objects.create(
        name="Queen of Apostles Seminary Senior School",
        code="QASS",
    )


@pytest.fixture
def academic_year(school):
    return AcademicYear.objects.create(
        school=school,
        name="2026",
        start_date="2026-01-01",
        end_date="2026-12-31",
    )


@pytest.fixture
def term(academic_year):
    return Term.objects.create(
        academic_year=academic_year,
        name="Term 1",
        number=1,
        start_date="2026-01-01",
        end_date="2026-04-30",
    )


@pytest.mark.django_db
def test_list_schools(api_client, school):
    response = api_client.get("/api/core/schools/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["name"] == school.name
    assert response.data[0]["code"] == school.code


@pytest.mark.django_db
def test_create_school(api_client):
    response = api_client.post(
        "/api/core/schools/",
        {
            "name": "Test School",
            "code": "TEST",
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["name"] == "Test School"
    assert School.objects.filter(code="TEST").exists()


@pytest.mark.django_db
def test_retrieve_school(api_client, school):
    response = api_client.get(
        f"/api/core/schools/{school.id}/"
    )

    assert response.status_code == 200
    assert response.data["id"] == str(school.id)


@pytest.mark.django_db
def test_update_school(api_client, school):
    response = api_client.patch(
        f"/api/core/schools/{school.id}/",
        {"name": "Updated School"},
        format="json",
    )

    assert response.status_code == 200
    school.refresh_from_db()
    assert school.name == "Updated School"


@pytest.mark.django_db
def test_delete_school(api_client, school):
    response = api_client.delete(
        f"/api/core/schools/{school.id}/"
    )

    assert response.status_code == 204
    assert not School.objects.filter(id=school.id).exists()


@pytest.mark.django_db
def test_list_academic_years(api_client, academic_year):
    response = api_client.get("/api/core/academic-years/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["name"] == "2026"
    assert response.data[0]["school_name"] == academic_year.school.name


@pytest.mark.django_db
def test_create_academic_year(api_client, school):
    response = api_client.post(
        "/api/core/academic-years/",
        {
            "school": str(school.id),
            "name": "2027",
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["name"] == "2027"
    assert AcademicYear.objects.filter(name="2027").exists()


@pytest.mark.django_db
def test_retrieve_academic_year(api_client, academic_year):
    response = api_client.get(
        f"/api/core/academic-years/{academic_year.id}/"
    )

    assert response.status_code == 200
    assert response.data["id"] == str(academic_year.id)


@pytest.mark.django_db
def test_update_academic_year(api_client, academic_year):
    response = api_client.patch(
        f"/api/core/academic-years/{academic_year.id}/",
        {"name": "2026 Updated"},
        format="json",
    )

    assert response.status_code == 200
    academic_year.refresh_from_db()
    assert academic_year.name == "2026 Updated"


@pytest.mark.django_db
def test_delete_academic_year(api_client, academic_year):
    response = api_client.delete(
        f"/api/core/academic-years/{academic_year.id}/"
    )

    assert response.status_code == 204
    assert not AcademicYear.objects.filter(
        id=academic_year.id
    ).exists()


@pytest.mark.django_db
def test_academic_year_rejects_invalid_dates(api_client, school):
    response = api_client.post(
        "/api/core/academic-years/",
        {
            "school": str(school.id),
            "name": "Invalid",
            "start_date": "2026-12-31",
            "end_date": "2026-01-01",
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_list_terms(api_client, term):
    response = api_client.get("/api/core/terms/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["name"] == "Term 1"
    assert response.data[0]["academic_year_name"] == "2026"


@pytest.mark.django_db
def test_create_term(api_client, academic_year):
    response = api_client.post(
        "/api/core/terms/",
        {
            "academic_year": str(academic_year.id),
            "name": "Term 2",
            "number": 2,
            "start_date": "2026-05-01",
            "end_date": "2026-08-31",
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["name"] == "Term 2"
    assert Term.objects.filter(number=2).exists()


@pytest.mark.django_db
def test_retrieve_term(api_client, term):
    response = api_client.get(
        f"/api/core/terms/{term.id}/"
    )

    assert response.status_code == 200
    assert response.data["id"] == str(term.id)


@pytest.mark.django_db
def test_update_term(api_client, term):
    response = api_client.patch(
        f"/api/core/terms/{term.id}/",
        {"name": "Updated Term"},
        format="json",
    )

    assert response.status_code == 200
    term.refresh_from_db()
    assert term.name == "Updated Term"


@pytest.mark.django_db
def test_delete_term(api_client, term):
    response = api_client.delete(
        f"/api/core/terms/{term.id}/"
    )

    assert response.status_code == 204
    assert not Term.objects.filter(id=term.id).exists()


@pytest.mark.django_db
def test_term_rejects_zero_number(api_client, academic_year):
    response = api_client.post(
        "/api/core/terms/",
        {
            "academic_year": str(academic_year.id),
            "name": "Invalid Term",
            "number": 0,
            "start_date": "2026-01-01",
            "end_date": "2026-04-30",
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_term_rejects_invalid_dates(api_client, academic_year):
    response = api_client.post(
        "/api/core/terms/",
        {
            "academic_year": str(academic_year.id),
            "name": "Invalid Term",
            "number": 2,
            "start_date": "2026-04-30",
            "end_date": "2026-01-01",
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 400
