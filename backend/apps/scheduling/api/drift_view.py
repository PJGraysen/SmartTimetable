"""Drift between two timetable versions - powers the 1b post-run diff view."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.scheduling.models import TimetableEntry, TimetableVersion


def _cells(version):
    m = {}
    qs = (
        TimetableEntry.objects
        .filter(timetable_version=version)
        .select_related("instructional_group", "lesson_requirement__subject")
    )
    for e in qs:
        gc = e.instructional_group.code if e.instructional_group else "?"
        sc = "?"
        lr = e.lesson_requirement
        if lr is not None:
            subj = getattr(lr, "subject", None)
            sc = (getattr(subj, "code", None)
                  or getattr(lr, "subject_code", None) or "?")
        m[(str(gc), e.day, e.period.number)] = str(sc)
    return m


class SchedulingDriftView(APIView):
    """GET /api/scheduling/drift/?a=<uuid>&b=<uuid>

    Returns per-group changed-cell counts and the raw changed keys.
    'a' = new version, 'b' = baseline. Both must belong to the same term.
    """

    def get(self, request):
        a_id = request.query_params.get("a")
        b_id = request.query_params.get("b")
        if not a_id or not b_id:
            return Response(
                {"detail": "Query params 'a' and 'b' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        a = TimetableVersion.objects.filter(pk=a_id).first()
        b = TimetableVersion.objects.filter(pk=b_id).first()
        if a is None or b is None:
            return Response(
                {"detail": "One or both versions not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if a.term_id != b.term_id:
            return Response(
                {"detail": "Versions belong to different terms."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ca, cb = _cells(a), _cells(b)
        by_group = {}
        changed = []
        for k in set(ca) | set(cb):
            if ca.get(k) == cb.get(k):
                continue
            g, day, pnum = k
            by_group[g] = by_group.get(g, 0) + 1
            changed.append({
                "group": g,
                "day": day,
                "period": pnum,
                "from": cb.get(k),
                "to": ca.get(k),
            })

        return Response({
            "a": {"id": str(a.pk), "name": a.name,
                  "created_at": a.created_at.isoformat()},
            "b": {"id": str(b.pk), "name": b.name,
                  "created_at": b.created_at.isoformat()},
            "total_changed": len(changed),
            "by_group": by_group,
            "changed": changed,
        })
