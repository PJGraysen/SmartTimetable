from django.shortcuts import render

# Create your views here.


# ---------------------------------------------------------------------
# Admin-facing read-only viewsets (Layer 1)
# ---------------------------------------------------------------------
from rest_framework import viewsets, filters, serializers
from rest_framework.permissions import BasePermission

from apps.audit.models import AuditLog, ErrorRecord


class _IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and getattr(u, "is_authenticated", False)
            and (u.is_superuser or u.is_staff)
        )


class AuditLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "created_at", "user", "user_username", "user_name",
            "action", "entity_type", "entity_id", "description", "ip_address",
        ]

    def get_user_name(self, obj):
        if not obj.user_id:
            return None
        return (
            f"{obj.user.first_name} {obj.user.last_name}".strip()
            or obj.user.username
        )


class ErrorRecordSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ErrorRecord
        fields = "__all__"


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user").order_by("-created_at")
    serializer_class = AuditLogSerializer
    permission_classes = [_IsAdmin]
    from rest_framework.pagination import PageNumberPagination as _PNP

    class _Pager(_PNP):
        page_size = 100
        page_size_query_param = "page_size"
        max_page_size = 1000

    pagination_class = _Pager
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["entity_type", "entity_id", "description", "action"]
    ordering_fields = ["created_at", "action", "entity_type"]
    ordering = ["-created_at"]


class ErrorRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ErrorRecord.objects.select_related("user").order_by("-occurred_at")
    serializer_class = ErrorRecordSerializer
    permission_classes = [_IsAdmin]
    from rest_framework.pagination import PageNumberPagination as _PNP2

    class _Pager2(_PNP2):
        page_size = 100
        page_size_query_param = "page_size"
        max_page_size = 1000

    pagination_class = _Pager2
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["subsystem", "operation", "error_code", "message"]
    ordering_fields = ["occurred_at", "severity", "status"]
    ordering = ["-occurred_at"]


# ---------------------------------------------------------------------
# Layer 3A ? heartbeat + active users
# ---------------------------------------------------------------------
from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers as _ser

from apps.audit.models import UserHeartbeat


class UserHeartbeatSerializer(_ser.ModelSerializer):
    username = _ser.CharField(source="user.username", read_only=True)
    first_name = _ser.CharField(source="user.first_name", read_only=True)
    last_name = _ser.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = UserHeartbeat
        fields = [
            "user", "username", "first_name", "last_name",
            "last_seen", "last_path", "user_agent", "ip_address",
        ]


class HeartbeatView(APIView):
    """POST /api/audit/heartbeat/ ? record the current user is active."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        path = (request.data.get("path") or "")[:500]

        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = (xff.split(",")[0].strip() if xff
              else request.META.get("REMOTE_ADDR") or None)
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:300]

        obj, _created = UserHeartbeat.objects.update_or_create(
            user=user,
            defaults={
                "last_path": path,
                "user_agent": ua,
                "ip_address": ip,
            },
        )

        # Broadcast to admin live feed
        try:
            from apps.audit.broadcast import broadcast
            broadcast({
                "type": "heartbeat",
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "last_path": path,
                "ip_address": ip,
                "last_seen": obj.last_seen.isoformat(),
            })
        except Exception:
            pass

        return Response({
            "ok": True,
            "last_seen": obj.last_seen,
        })


class ActiveUsersView(APIView):
    """GET /api/audit/active-users/?window=120 ? admin only.

    Returns users whose heartbeat is within the last N seconds.
    """

    permission_classes = [_IsAdmin]

    def get(self, request):
        try:
            window = int(request.query_params.get("window", 120))
        except ValueError:
            window = 120
        window = max(30, min(window, 3600))

        cutoff = timezone.now() - timedelta(seconds=window)
        rows = (
            UserHeartbeat.objects
            .filter(last_seen__gte=cutoff)
            .select_related("user")
            .order_by("-last_seen")
        )
        return Response({
            "window_seconds": window,
            "count": rows.count(),
            "users": UserHeartbeatSerializer(rows, many=True).data,
        })
