"""REST API for Notification + ApprovalRequest."""
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.core.models import ApprovalRequest, Notification


# ----- Serializers -----
class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_username = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id", "kind", "title", "body", "url",
            "is_read", "is_archived", "is_starred",
            "created_at", "read_at",
            "sender", "sender_name", "sender_username",
            "parent", "attachment", "attachment_name", "attachment_url",
            "replies_count",
        )
        read_only_fields = fields

    def get_sender_name(self, obj):
        if not obj.sender:
            return None
        return (f"{obj.sender.first_name} {obj.sender.last_name}".strip()) or obj.sender.username

    def get_sender_username(self, obj):
        return obj.sender.username if obj.sender else None

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        try:
            return obj.attachment.url
        except Exception:
            return None

    def get_replies_count(self, obj):
        return obj.replies.count()


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Used when a user sends a message to another user."""
    recipient_id = serializers.IntegerField(write_only=True)
    parent_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    attachment = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Notification
        fields = (
            "recipient_id", "parent_id", "kind", "title", "body", "url",
            "attachment", "attachment_name",
        )

    def validate_recipient_id(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Recipient not found or inactive.")
        return value

    def validate_parent_id(self, value):
        if value is None:
            return None
        try:
            Notification.objects.get(id=value)
        except Notification.DoesNotExist:
            raise serializers.ValidationError("Parent message not found.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        recipient_id = validated_data.pop("recipient_id")
        parent_id = validated_data.pop("parent_id", None)
        attachment = validated_data.pop("attachment", None)
        attachment_name = validated_data.get("attachment_name") or ""
        if attachment:
            attachment_name = attachment_name or attachment.name
        return Notification.objects.create(
            recipient_id=recipient_id,
            sender=request.user,
            parent_id=parent_id,
            attachment=attachment,
            attachment_name=attachment_name,
            **{k: v for k, v in validated_data.items() if k != "attachment_name"},
        )


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
class NotificationViewSet(viewsets.ModelViewSet):
    """Notifications inbox + send + archive + star."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == "create":
            return NotificationCreateSerializer
        return NotificationSerializer

    def get_queryset(self):
        return (
            Notification.objects
            .filter(recipient=self.request.user)
            .select_related("recipient", "sender", "parent")
            .order_by("-created_at")
        )

    @action(detail=False, methods=["get"], url_path="recipients")
    def recipients(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")
        data = []
        for u in users:
            if u.id == request.user.id:
                continue
            name = (f"{u.first_name} {u.last_name}".strip()) or u.username
            data.append({"id": u.id, "name": name, "username": u.username})
        return Response(data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        n = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
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

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        obj = self.get_object()
        obj.is_archived = True
        obj.save(update_fields=["is_archived"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request, pk=None):
        obj = self.get_object()
        obj.is_archived = False
        obj.save(update_fields=["is_archived"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"], url_path="star")
    def star(self, request, pk=None):
        obj = self.get_object()
        obj.is_starred = True
        obj.save(update_fields=["is_starred"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"], url_path="unstar")
    def unstar(self, request, pk=None):
        obj = self.get_object()
        obj.is_starred = False
        obj.save(update_fields=["is_starred"])
        return Response(self.get_serializer(obj).data)


# ----- Approval Request ViewSet -----
class ApprovalRequestViewSet(viewsets.ModelViewSet):
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
