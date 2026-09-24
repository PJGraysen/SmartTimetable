import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.library.models import Book


@pytest.fixture
def client_unauth():
    return APIClient()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="libadmin", password="x")
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
def test_books_list_requires_auth(client_unauth):
    resp = client_unauth.get("/api/library/books/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_books_list_authenticated_no_perm(auth_client):
    # authenticated but without library.view_book -> 403
    resp = auth_client.get("/api/library/books/")
    assert resp.status_code in (403,)


@pytest.mark.django_db
def test_books_list_with_perm(db):
    from django.contrib.auth.models import Permission
    user = User.objects.create_user(username="viewer", password="x")
    perm = Permission.objects.get(
        content_type__app_label="library", codename="view_book",
    )
    user.user_permissions.add(perm)
    user = User.objects.get(id=user.id)

    c = APIClient()
    c.force_authenticate(user=user)
    Book.objects.create(title="Visible")
    resp = c.get("/api/library/books/")
    assert resp.status_code == 200
    payload = resp.json()
    items = payload.get("results", payload) if isinstance(payload, dict) else payload
    assert len(items) >= 1


@pytest.mark.django_db
def test_dashboard_requires_auth(client_unauth):
    resp = client_unauth.get("/api/library/dashboard/")
    assert resp.status_code in (401, 403)
