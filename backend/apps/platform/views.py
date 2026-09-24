from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .applications import applications_for_user


def _serialize_user(user) -> dict | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    display_name = user.get_full_name().strip() or user.get_username()
    return {
        "id": user.id,
        "username": user.get_username(),
        "display_name": display_name,
        "is_superuser": bool(user.is_superuser),
    }


def _serialize_applications(user) -> list[dict]:
    return [a.to_dict() for a in applications_for_user(user)]


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request):
    username = str(request.data.get("username", "")).strip()
    password = str(request.data.get("password", ""))

    if not username or not password:
        return Response(
            {"detail": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"detail": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if not user.is_active:
        return Response(
            {"detail": "Account is inactive."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    login(request, user)
    return Response({
        "user": _serialize_user(user),
        "applications": _serialize_applications(user),
    })


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response({"detail": "Signed out."})


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def me_view(request):
    user = request.user if getattr(request.user, "is_authenticated", False) else None
    return Response({
        "user": _serialize_user(user),
        "applications": _serialize_applications(user),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def applications_view(request):
    return Response({
        "applications": _serialize_applications(request.user),
    })
