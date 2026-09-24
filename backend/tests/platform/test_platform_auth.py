import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="platform-admin",
        password="adminpass123",
        email="admin@example.com",
    )


@pytest.fixture
def normal_user(db):
    return User.objects.create_user(
        username="platform-teacher",
        password="teachpass123",
    )


@pytest.mark.django_db
def test_login_valid_credentials(superuser):
    client = APIClient()
    resp = client.post(
        "/api/platform/auth/login/",
        {"username": "platform-admin", "password": "adminpass123"},
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["username"] == "platform-admin"
    assert data["user"]["is_superuser"] is True
    assert len(data["applications"]) >= 1
    slugs = {a["slug"] for a in data["applications"]}
    assert {"timetable", "academic_analysis", "library"} <= slugs


@pytest.mark.django_db
def test_login_invalid_credentials(db):
    client = APIClient()
    resp = client.post(
        "/api/platform/auth/login/",
        {"username": "nobody", "password": "wrong"},
        format="json",
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_login_missing_fields(db):
    client = APIClient()
    resp = client.post("/api/platform/auth/login/", {}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_me_unauthenticated(db):
    client = APIClient()
    resp = client.get("/api/platform/auth/me/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"] is None
    assert data["applications"] == []


@pytest.mark.django_db
def test_me_authenticated(superuser):
    client = APIClient()
    client.force_authenticate(user=superuser)
    resp = client.get("/api/platform/auth/me/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["username"] == "platform-admin"
    assert len(data["applications"]) >= 1


@pytest.mark.django_db
def test_logout(superuser):
    client = APIClient()
    client.force_authenticate(user=superuser)
    resp = client.post("/api/platform/auth/logout/", format="json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_applications_requires_auth(db):
    client = APIClient()
    resp = client.get("/api/platform/applications/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_superuser_sees_all_applications(superuser):
    client = APIClient()
    client.force_authenticate(user=superuser)
    resp = client.get("/api/platform/applications/")
    assert resp.status_code == 200
    slugs = {a["slug"] for a in resp.json()["applications"]}
    assert {"timetable", "academic_analysis", "library"} <= slugs


@pytest.mark.django_db
def test_normal_user_sees_open_applications(normal_user):
    client = APIClient()
    client.force_authenticate(user=normal_user)
    resp = client.get("/api/platform/applications/")
    assert resp.status_code == 200
    slugs = {a["slug"] for a in resp.json()["applications"]}
    # All three have empty required_permissions -> visible
    assert {"timetable", "academic_analysis", "library"} <= slugs
