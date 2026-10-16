"""Read-only scope discovery endpoint for the 1b scope picker."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.core.models import Term
from apps.scheduling.models import InstructionalGroup, LessonRequirement


def _is_uuid(s):
    try:
        import uuid; uuid.UUID(str(s)); return True
    except (ValueError, TypeError):
        return False


def _discover_grades():
    codes = list(
        InstructionalGroup.objects
        .filter(is_active=True)
        .values_list("code", flat=True)
    )
    prefixes = set()
    for c in codes:
        c = str(c).strip().upper()
        if len(c) >= 2 and c[-1] in ("E", "W"):
            prefixes.add(c[:-1])
    out = []
    for p in sorted(prefixes, key=lambda s: (len(s), s)):
        lbl = "Form 4" if p == "4" else "Grade %s" % p
        groups = sorted(
            str(c).strip().upper() for c in codes
            if str(c).strip().upper().startswith(p)
        )
        out.append({"kind": "grade", "id": p, "label": lbl, "groups": groups})
    return out


def _discover_subjects():
    seen = {}
    qs = LessonRequirement.objects.filter(is_active=True).select_related("subject")
    for lr in qs:
        subj = getattr(lr, "subject", None)
        if subj is None:
            continue
        code = getattr(subj, "code", None)
        if not code:
            continue
        code = str(code).strip().upper()
        if code in seen:
            continue
        seen[code] = {
            "kind": "subject",
            "id": code,
            "label": getattr(subj, "name", None) or code,
            "code": code,
        }
    return [seen[k] for k in sorted(seen)]


class SchedulingScopeListView(APIView):
    permission_classes = [IsAuthenticated]

    """GET /api/scheduling/scopes/?term=<name_or_id>"""

    def get(self, request):
        term_ref = request.query_params.get("term")
        qs = Term.objects.all()
        term = None
        if term_ref:
            term = qs.filter(name__iexact=term_ref).first()
            if term is None and _is_uuid(term_ref):
                term = qs.filter(pk=term_ref).first()
        else:
            term = qs.order_by("-created_at").first()

        if term is None:
            return Response(
                {"detail": "No term found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from apps.scheduling.models import TimetableVersion, SchedulingRun
        # Last 3 approved runs of this term, newest first. Each entry
        # exposes the linked version's id, name, and approval timestamp.
        approved_runs = (
            SchedulingRun.objects
            .filter(
                term=term,
                approved_at__isnull=False,
                timetable_version__isnull=False,
            )
            .order_by("-approved_at")
            .select_related("timetable_version")[:3]
        )
        baselines = [
            {
                "id": str(r.timetable_version_id),
                "name": r.timetable_version.name,
                "version_number": r.timetable_version.version_number,
                "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            }
            for r in approved_runs
        ]
        active_version = (
            TimetableVersion.objects
            .filter(term=term, is_active=True)
            .order_by("-created_at")
            .first()
        )

        return Response({
            "term": {"id": str(term.pk), "name": term.name},
            "master": {"kind": "master", "id": None,
                       "label": "Master (full re-solve)"},
            "grades": _discover_grades(),
            "subjects": _discover_subjects(),
            "baselines": baselines,
            "active_baseline_id": str(active_version.pk) if active_version else None,
        })
