"""REST API for Notification + ApprovalRequest."""
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import ApprovalRequest, Notification


# ----- Serializers -----
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "kind", "title", "body", "url", "is_read", "created_at", "read_at")
        read_only_fields = fields


class ApprovalRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = (
            "id", "kind", "status", "title", "body",
            "requested_by", "requested_by_name",
            "assigned_to", "assigned_to_name",
            "target_type", "target_id", "payload",
            "created_at", "decided_at", "decision_note",
        )
        read_only_fields = (
            "id", "status", "requested_by", "assigned_to",
            "created_at", "decided_at", "decision_note",
        )

    def get_requested_by_name(self, obj):
        u = obj.requested_by
        return u.get_full_name() or u.username if u else ""

    def get_assigned_to_name(self, obj):
        u = obj.assigned_to
        return u.get_full_name() or u.username if u else ""


# ----- Notification ViewSet -----
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """A user only sees their own notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        n = Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True,
        )
        return Response({"marked_read": n})

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        obj = self.get_object()
        obj.mark_read()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        n = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread": n})


# ----- Approval Request ViewSet -----
class ApprovalRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for approvals. A user sees:
      - requests they need to approve (assigned_to = them)
      - requests they've made (requested_by = them)
    """
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        from django.db.models import Q
        return ApprovalRequest.objects.filter(
            Q(assigned_to=u) | Q(requested_by=u)
        ).select_related("requested_by", "assigned_to")

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        obj = self.get_object()
        if obj.assigned_to_id != request.user.id and not request.user.is_superuser:
            return Response({"detail": "Not assigned to you."}, status=403)
        note = request.data.get("note", "")
        from apps.core.notifications import resolve_approval
        resolve_approval(obj, approved=True, by_user=request.user, note=note)
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        obj = self.get_object()
        if obj.assigned_to_id != request.user.id and not request.user.is_superuser:
            return Response({"detail": "Not assigned to you."}, status=403)
        note = request.data.get("note", "")
        from apps.core.notifications import resolve_approval
        resolve_approval(obj, approved=False, by_user=request.user, note=note)
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=["get"], url_path="pending-count")
    def pending_count(self, request):
        n = ApprovalRequest.objects.filter(
            assigned_to=request.user,
            status=ApprovalRequest.Status.PENDING,
        ).count()
        return Response({"pending": n})
