"""Extra LessonRequirement views: copy + validate."""
from __future__ import annotations

from collections import Counter, defaultdict

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import LessonRequirement
from apps.core.models import Term

from .lr_contract import contract_for


def _resolve_term(param):
    if not param:
        return None
    t = None
    if isinstance(param, str) and len(param) == 36:
        t = Term.objects.filter(id=param).first()
    if t is None:
        t = Term.objects.filter(name__iexact=str(param)).first()
    return t


class LessonRequirementCopyView(APIView):
    """POST {from_term, to_term, apply} -> clone active LRs."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        source = _resolve_term(request.data.get("from_term"))
        target = _resolve_term(request.data.get("to_term"))
        apply_ = bool(request.data.get("apply", True))

        if source is None or target is None:
            return Response(
                {"detail": "from_term and to_term must each be a term id or name."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if source.pk == target.pk:
            return Response(
                {"detail": "Source and target must differ."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        src_lrs = [
            lr for lr in (
                LessonRequirement.objects
                .filter(term=source, is_active=True)
                .select_related("subject", "instructional_group", "teacher")
            )
            if lr.instructional_group is None
            or lr.instructional_group.is_active
        ]

        if not apply_:
            return Response({
                "source": source.name,
                "target": target.name,
                "source_active_lrs": len(src_lrs),
                "applied": False,
            })

        created = updated = unchanged = 0
        with transaction.atomic():
            for src in src_lrs:
                existing = LessonRequirement.objects.filter(
                    term=target,
                    instructional_group=src.instructional_group,
                    subject=src.subject,
                    requirement_type=src.requirement_type,
                ).first()
                if existing is None:
                    LessonRequirement.objects.create(
                        term=target,
                        instructional_group=src.instructional_group,
                        subject=src.subject,
                        teacher=src.teacher,
                        requirement_type=src.requirement_type,
                        lessons_per_week=src.lessons_per_week,
                        is_active=src.is_active,
                    )
                    created += 1
                else:
                    changed = (
                        existing.lessons_per_week != src.lessons_per_week
                        or existing.teacher_id != src.teacher_id
                        or not existing.is_active
                    )
                    if changed:
                        existing.lessons_per_week = src.lessons_per_week
                        existing.teacher = src.teacher
                        existing.is_active = True
                        existing.save(update_fields=[
                            "lessons_per_week", "teacher", "is_active",
                        ])
                        updated += 1
                    else:
                        unchanged += 1

        return Response({
            "source": source.name,
            "target": target.name,
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "target_active": LessonRequirement.objects.filter(
                term=target, is_active=True
            ).count(),
        })


class LessonRequirementValidateView(APIView):
    """GET ?term=<id or name> -> per-group contract report."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        term = _resolve_term(request.query_params.get("term"))
        if term is None:
            return Response(
                {"detail": "term query parameter required (id or name)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        by_group = defaultdict(Counter)
        for lr in (
            LessonRequirement.objects
            .filter(term=term, is_active=True)
            .select_related("subject", "instructional_group")
        ):
            if lr.instructional_group is None or lr.subject is None:
                continue
            if lr.subject.code == "GST":
                continue
            key = (lr.subject.code, lr.requirement_type)
            by_group[lr.instructional_group.code][key] += lr.lessons_per_week

        report = []
        for gc in sorted(by_group):
            contract = contract_for(gc)
            if contract is None:
                continue
            scheduled = by_group[gc]
            short, over, extra = [], [], []
            for key, want in contract.items():
                have = scheduled.get(key, 0)
                if have < want:
                    short.append({"subject": key[0], "type": key[1],
                                  "have": have, "want": want})
                elif have > want:
                    over.append({"subject": key[0], "type": key[1],
                                 "have": have, "want": want})
            for key, have in scheduled.items():
                if key not in contract:
                    extra.append({"subject": key[0], "type": key[1],
                                  "have": have})
            report.append({
                "group": gc,
                "short": short,
                "over": over,
                "extra": extra,
                "ok": not (short or over or extra),
            })

        return Response({
            "term": term.name,
            "term_id": str(term.id),
            "report": report,
            "groups_ok": all(r["ok"] for r in report),
        })
