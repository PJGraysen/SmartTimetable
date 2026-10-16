"""Transient notification feed for the frontend banner.

No Notification model, no migration. Derives events from the
SchedulingRun table: completed, failed, and approved. Frontend polls
this endpoint on a short interval.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.scheduling.models import SchedulingRun, SchedulingRunStatus


def _iso(dt):
    return dt.isoformat() if dt else None


class SchedulingNotificationsView(APIView):
    """GET /api/scheduling/notifications/?since=<iso>

    Returns up to 20 recent events. If 'since' is provided, only
    events strictly newer than that timestamp are returned.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        since = request.query_params.get("since")
        qs = (
            SchedulingRun.objects
            .select_related("term")
            .order_by("-updated_at")[:20]
        )

        events = []
        for r in qs:
            ts = r.updated_at
            if since and ts is not None and ts.isoformat() <= since:
                continue

            status = str(getattr(r, "status", "") or "")
            approved = bool(getattr(r, "is_approved", False))

            kind = None
            title = None
            level = "info"
            if status == SchedulingRunStatus.FAILED:
                kind, title, level = "generation_failed", "Generation failed", "error"
            elif status == SchedulingRunStatus.COMPLETED and approved:
                kind, title, level = "generation_approved", "Version approved", "success"
            elif status == SchedulingRunStatus.COMPLETED:
                kind, title, level = "generation_done", "Generation completed", "success"

            if kind is None:
                continue

            events.append({
                "id": str(r.pk),
                "kind": kind,
                "level": level,
                "title": title,
                "term": getattr(r.term, "name", None) if r.term else None,
                "status": status,
                "approved": approved,
                "at": _iso(ts),
                "message": (r.error_message[:200]
                            if status == SchedulingRunStatus.FAILED else None),
            })

        return Response({"events": events, "count": len(events)})
